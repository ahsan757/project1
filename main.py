from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import motor.motor_asyncio
from datetime import datetime
from typing import Optional

# Database connection
client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
db = client["yarn_db"]  # Use your database name here
requests_collection = db["requests"]
received_collection = db["received"]  # New collection for received yarn
vendor_collection = db["vendor"]  # New collection for vendors

app = FastAPI()

# Define the Pydantic model for the yarn request
class YarnRequest(BaseModel):
    count: int
    content: str
    spun_type: str
    bags: int
    kgs: float
    status: str = "pending"  # Default status is 'pending'

# Model to represent received yarn
class YarnReceived(BaseModel):
    spun_type: str
    kgs_received: float
    received_date: datetime
    vendor_id: str  # New field for vendor_id

# Model for vendor registration
class Vendor(BaseModel):
    company_name: str
    broker_name: str
    contract_type: str
    contact: str
    gst_number: str
    prefix: str

# Route to create a vendor
@app.post("/register_vendor/")
async def register_vendor(vendor: Vendor):
    # Generate a unique vendor_id starting with the prefix
    last_vendor = await vendor_collection.find_one({"prefix": vendor.prefix}, sort=[("vendor_id", -1)])
    if last_vendor:
        new_vendor_id = f"{vendor.prefix}{int(last_vendor['vendor_id'][len(vendor.prefix):]) + 1}"
    else:
        new_vendor_id = f"{vendor.prefix}1"

    # Create a new vendor document
    vendor_data = vendor.dict()
    vendor_data["vendor_id"] = new_vendor_id
    result = await vendor_collection.insert_one(vendor_data)
    return {"message": "Vendor registered successfully", "vendor_id": new_vendor_id}

# Route to create a yarn request
@app.post("/request_yarn/")
async def request_yarn(request: YarnRequest):
    request_data = request.dict()
    request_data['created_at'] = datetime.now()
    result = await requests_collection.insert_one(request_data)
    return {"message": "Request created", "request_id": str(result.inserted_id)}

# Route to receive yarn and update the request
@app.put("/receive_yarn/")
async def receive_yarn(received_data: YarnReceived):
    # Validate vendor ID
    vendor = await vendor_collection.find_one({"vendor_id": received_data.vendor_id})
    if not vendor:
        raise HTTPException(status_code=400, detail="Please register the vendor first.")

    # Find requests with matching spun_type and check status
    request = await requests_collection.find_one({
        "spun_type": received_data.spun_type,
        "status": "pending"
    })

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Update the received yarn
    remaining_kgs = request['kgs'] - received_data.kgs_received
    
    # Add received yarn details to the 'received' collection
    received_entry = {
        "spun_type": received_data.spun_type,
        "kgs_received": received_data.kgs_received,
        "received_date": received_data.received_date,
        "request_id": str(request["_id"]),
        "vendor_id": received_data.vendor_id  # Include vendor_id in the received entry
    }
    await received_collection.insert_one(received_entry)

    # Update the request in the 'requests' collection
    if remaining_kgs <= 0:
        # If the received yarn completes the request, update status to 'completed'
        update_data = {
            "status": "completed",
            "received_at": datetime.now()
        }
    else:
        update_data = {
            "kgs": remaining_kgs
        }

    # Update request in the database
    await requests_collection.update_one(
        {"_id": request["_id"]},
        {"$set": update_data}
    )

    return {"message": "Yarn received successfully", "remaining_kgs": remaining_kgs}
