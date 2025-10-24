from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import motor.motor_asyncio
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import uuid
from datetime import datetime
from fastapi.responses import StreamingResponse
import io
import csv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import uuid
import io

# Database connection
client = motor.motor_asyncio.AsyncIOMotorClient('mongodb+srv://Ahsan12:Ahsan12@botss.rvm4jx6.mongodb.net/')
db = client["yarn_db"]
requests_collection = db["requests"]
received_collection = db["received"]
vendor_collection = db["vendor"]
DB_NAME = "order_system"
ORDERS_COLLECTION_NAME = "orders"
KNITTING_COLLECTION_NAME = "knitting"
DYING_COLLECTION_NAME = "dying"
TRIM_COLLECTION_NAME="triming"
ADMIN_COLLECTION="admin"
db = client[DB_NAME]
orders_collection = db[ORDERS_COLLECTION_NAME]
knitting_collection = db[KNITTING_COLLECTION_NAME]
dying_collection = db[DYING_COLLECTION_NAME]
trim_collection=db[TRIM_COLLECTION_NAME]
admin_collection=db[ADMIN_COLLECTION]

app = FastAPI()

# Define the Pydantic model for the yarn request
class YarnRequest(BaseModel):
    count: int
    content: str
    spun_type: str
    bags: int
    kgs: float
    vendor_id:str
    order_no:str
    status: str = "pending"

# Model to represent received yarn
class YarnReceived(BaseModel):
    spun_type: str
    kgs_received: float
    bags_recevied:int
    received_date: datetime
    vendor_id: str
    order_no:str

# Model for vendor registration
class Vendor(BaseModel):
    company_name: str
    broker_name: str
    contract_type: str
    contact: str
    gst_number: str
    prefix: str
class Label(BaseModel):
    vendor_id: str
    quality: str
    printed_woven: str  # Can be either 'Printed' or 'Woven'
    elastic_type: str  # Either 'in-house' or 'outsourced'
    elastic_vendor_id: Optional[str] = None  # Optional vendor ID if outsourced
    trims: List[str] = []  # List of trim items (e.g., Poly Bag, Carton, Belly Band)

# Define the Order Pydantic model with additional trim fields
class Order(BaseModel):
    customer_name: str
    order_number: str
    bags:int
    company_order_number: str
    yarn_count: int
    content: str
    spun: str
    sizes: List[str]
    knitting_type: str
    dyeing_type: str
    dyeing_color:str
    finishing_type: str
    po_number: str
    labels: Optional[List[Label]] = None  # Up to 4 labels (can be empty)

    # Optional: Convert MongoDB ObjectId to string for response
    class Config:
        json_encoders = {
            ObjectId: str
        }

# Define the model for yarn tracking in the knitting department
class YarnTracking(BaseModel):
    po_number: str  # PO number for which yarn is tracked
    available_yarn: float  # The total available yarn for the PO number
    processed_yarn: float  # The amount of yarn processed for the PO number

# Define the model for dying record
class DyingRecord(BaseModel):
    po_number: str  # PO number for which yarn is tracked
    available_yarn: float  # The total available yarn for the PO number
    processed_yarn: float 
class trimRecord(BaseModel):
    po_number: str  # PO number for which yarn is tracked
    available_yarn: float  # The total available yarn for the PO number
    completed_yarn: float 


# ---------------- EXISTING ROUTES ---------------- #

@app.post("/register_vendor/")
async def register_vendor(vendor: Vendor):
    last_vendor = await vendor_collection.find_one({"prefix": vendor.prefix}, sort=[("vendor_id", -1)])
    if last_vendor:
        new_vendor_id = f"{vendor.prefix}{int(last_vendor['vendor_id'][len(vendor.prefix):]) + 1}"
    else:
        new_vendor_id = f"{vendor.prefix}1"

    vendor_data = vendor.dict()
    vendor_data["vendor_id"] = new_vendor_id
    await vendor_collection.insert_one(vendor_data)
    return {"message": "Vendor registered successfully", "vendor_id": new_vendor_id}


@app.post("/request_yarn/")
async def request_yarn(request: YarnRequest):
    request_data = request.dict()
    request_data['created_at'] = datetime.now()
    result = await requests_collection.insert_one(request_data)
    return {"message": "Request created", "request_id": str(result.inserted_id)}


@app.put("/receive_yarn/")
async def receive_yarn(received_data: YarnReceived):
    vendor = await vendor_collection.find_one({"vendor_id": received_data.vendor_id})
    if not vendor:
        raise HTTPException(status_code=400, detail="Please register the vendor first.")

    request = await requests_collection.find_one({
        "order_no":received_data.order_no,
        "spun_type": received_data.spun_type,
        "status": "pending"
    })
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    remaining_kgs = request['kgs'] - received_data.kgs_received
    remaining_bags=request['bags']-received_data.bags_recevied

    received_entry = {
        "spun_type": received_data.spun_type,
        "kgs_received": received_data.kgs_received,
        "bags_recevied":received_data.bags_recevied,
        "received_date": received_data.received_date,
        "order_no":received_data.order_no,
        "vendor_id": received_data.vendor_id
    }
    await received_collection.insert_one(received_entry)

    if remaining_kgs <= 0:
        update_data = {"status": "completed", "received_at": datetime.now()}
    else:
        update_data = {"kgs": remaining_kgs,"bags":remaining_bags}

    await requests_collection.update_one(
        {"_id": request["_id"]},
        {"$set": update_data}
    )

    return {"message": "Yarn received successfully", "remaining_kgs": remaining_kgs}


# ---------------- NEW ROUTES ---------------- #

# View a specific vendor by vendor_id
@app.get("/view_vendor/{vendor_id}")
async def view_vendor(vendor_id: str):
    vendor = await vendor_collection.find_one({"vendor_id": vendor_id}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


# Delete a vendor by vendor_id
@app.delete("/delete_vendor/{vendor_id}")
async def delete_vendor(vendor_id: str):
    result = await vendor_collection.delete_one({"vendor_id": vendor_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return {"message": f"Vendor with ID {vendor_id} deleted successfully"}


# View all yarn requests (optionally filter by status)
@app.get("/view_yarn/")
async def view_yarn(status: Optional[str] = None):
    query = {"status": status} if status else {}
    yarn_cursor = requests_collection.find(query, {"_id": 0})
    yarn_list = await yarn_cursor.to_list(length=None)
    if not yarn_list:
        raise HTTPException(status_code=404, detail="No yarn requests found")
    return yarn_list
@app.get("/view_all_yarn")
async def get_all_yarn_tracking():
    # Fetch all records from the knitting collection
    total_yarn = await received_collection.find().to_list(length=100)  # Limit to 100 records (optional)
    
    total_yarn = convert_objectid_to_str(total_yarn)
    
    if total_yarn:
        return total_yarn
    else:
        raise HTTPException(status_code=404, detail="No yarn tracking records found")
@app.get("/view_all_vendors")
async def get_all_yarn_tracking():
    # Fetch all records from the knitting collection
    total_vendors = await vendor_collection.find().to_list(length=100)  # Limit to 100 records (optional)
    
    total_vendors = convert_objectid_to_str(total_vendors)
    
    if total_vendors:
        return total_vendors
    else:
        raise HTTPException(status_code=404, detail="No vendor records found")





def convert_objectid_to_str(data):
    """Recursively converts ObjectId to string in the data."""
    if isinstance(data, dict):
        return {key: convert_objectid_to_str(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_objectid_to_str(item) for item in data]
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data




# Function to create a knitting record when an order is received
async def create_knitting_record(po_number: str, yarn_count: int):
    knitting_data = {
        "po_number": po_number,
        "available_yarn": yarn_count,
        "processed_yarn": 0,
        "today_recive":0,
        "totay_deleviry":0
    }
    # Insert the knitting data into the knitting collection
    await knitting_collection.insert_one(knitting_data)
async def create_triming_record(po_number: str):
    trim_data = {
        "po_number": po_number,
        "available_yarn": 0,
        "processed_yarn": 0,
        "today_recive":0,
        "totay_deleviry":0
    }
    # Insert the knitting data into the knitting collection
    await trim_collection.insert_one(trim_data)

# Function to create a dying record when yarn is processed
async def create_dying_record(po_number: str):
    dying_data = {
        "po_number": po_number,
        "available_yarn": 0,
        "processed_yarn": 0,
        "today_recive":0,
        "totay_deleviry":0
    }
    # Insert the dying data into the dying collection
    await dying_collection.insert_one(dying_data)
async def create_admin_record(po_number: str,yarn_count: int):
    admin_data = {
        "po_number": po_number,
        "total_given_yarn": yarn_count,
        "processed_yarn": 0
    }
    # Insert the dying data into the dying collection
    await admin_collection.insert_one(admin_data)

# Endpoint to receive and store the order in MongoDB
@app.post("/receive_order/")
async def receive_order(order: Order):
    # Insert the order into the MongoDB collection
    order_dict = order.dict()  # Convert Pydantic model to dictionary
    result = await orders_collection.insert_one(order_dict)  # Insert into MongoDB
    
    # Create the corresponding knitting record (initial yarn tracking)
    await create_knitting_record(order.po_number, order.yarn_count)
    await create_triming_record(order.po_number)
    await create_dying_record(order.po_number)
    await create_admin_record(order.po_number, order.yarn_count)

    # Return success response with the order's MongoDB ID and PO number
    return {"message": "Order received successfully!", "order_id": str(result.inserted_id), "po_number": order.po_number}

# Endpoint to change processed yarn for a specific PO number
@app.put("/knitting/process_yarn/")
async def process_yarn(po_number: str, amount: float,deliver:float):
    # Find the record for the given PO number in the knitting collection
    knitting_record = await knitting_collection.find_one({"po_number": po_number})
    dying_record = await dying_collection.find_one({"po_number": po_number})
    
    if knitting_record:
        # Check if there is enough available yarn to process
        if knitting_record['available_yarn'] >= amount:
            new_available_yarn = knitting_record['available_yarn'] - amount
            new_processed_yarn = knitting_record['processed_yarn'] + deliver
            new_dying_yarn=dying_record['available_yarn']+ deliver

            # Update the knitting record
            await knitting_collection.update_one(
                {"po_number": po_number},
                {"$set": {"available_yarn": new_available_yarn, "processed_yarn": new_processed_yarn}}
            )
            await dying_collection.update_one(
                {"po_number": po_number,},
                {"$set": {"available_yarn": new_dying_yarn}}
            )

            # Create a new record in the dying collection
            

            return {"message": "Yarn processed successfully!", "po_number": po_number, "new_available_yarn": new_available_yarn, "new_processed_yarn": new_processed_yarn}
        else:
            raise HTTPException(status_code=400, detail="Not enough available yarn to process")
    else:
        raise HTTPException(status_code=404, detail="PO number not found in knitting department")
@app.put("/dying/process_yarn/")
async def dye_yarn(po_number: str, amount: float,deliver:float):
    # Find the record for the given PO number in the knitting collection

    trimrecord=await trim_collection.find_one({"po_number": po_number})
    dying_record = await dying_collection.find_one({"po_number": po_number})    
    if dying_record:
        # Check if there is enough available yarn to process
        if dying_record['available_yarn'] >= amount:
            new_available_yarn = dying_record['available_yarn'] - amount
            new_processed_yarn = dying_record['processed_yarn'] + deliver
            new_trim_yarn=trimrecord['available_yarn']+ deliver
            

            # Update the knitting record
            await dying_collection.update_one(
                {"po_number": po_number},
                {"$set": {"available_yarn": new_available_yarn, "processed_yarn": new_processed_yarn}}
            )
            await trim_collection.update_one(
                {"po_number": po_number,},
                {"$set": {"available_yarn": new_trim_yarn}}
            )

            # Create a new record in the dying collection
            

            return {"message": "Yarn processed successfully!", "po_number": po_number, "new_available_yarn": new_available_yarn, "new_processed_yarn": new_processed_yarn}
        else:
            raise HTTPException(status_code=400, detail="Not enough available yarn to process")
    else:
        raise HTTPException(status_code=404, detail="PO number not found in knitting department")

@app.put("/trim/process_yarn/")
async def trim_yarn(po_number: str, amount: float,deliver:float):
    # Find the record for the given PO number in the knitting collection
    
    
    trimrecord=await trim_collection.find_one({"po_number": po_number})
    adminrecord=await admin_collection.find_one({"po_number": po_number})
    
    if trimrecord:
        # Check if there is enough available yarn to process
        if trimrecord['available_yarn'] >= amount:
            new_available_yarn = trimrecord['available_yarn'] - amount
            new_processed_yarn = trimrecord['processed_yarn'] + deliver
            final_product=adminrecord['processed_yarn']+ deliver

            # Update the knitting record
            await trim_collection.update_one(
                {"po_number": po_number},
                {"$set": {"available_yarn": new_available_yarn, "processed_yarn": new_processed_yarn}}
            )
            await admin_collection.update_one(
                {"po_number": po_number,},
                {"$set": {"processed_yarn": final_product}}
            )

            # Create a new record in the dying collection
            

            return {"message": "Yarn processed successfully!", "po_number": po_number, "new_available_yarn": new_available_yarn, "new_processed_yarn": new_processed_yarn}
        else:
            raise HTTPException(status_code=400, detail="Not enough available yarn to process")
    else:
        raise HTTPException(status_code=404, detail="PO number not found in knitting department")


# Endpoint to retrieve yarn tracking for a specific PO number
@app.get("/knitting/yarn/")
async def get_all_yarn_tracking():
    # Fetch all records from the knitting collection
    knitting_records = await knitting_collection.find().to_list(length=100)  # Limit to 100 records (optional)
    
    # Convert ObjectId to string for all knitting records
    knitting_records = convert_objectid_to_str(knitting_records)
    
    if knitting_records:
        return {"knitting_records": knitting_records}
    else:
        raise HTTPException(status_code=404, detail="No yarn tracking records found in knitting department")

@app.get("/dying/yarn/")
async def get_all_yarn_tracking():
    # Fetch all records from the knitting collection
    dying_records = await dying_collection.find().to_list(length=100)  # Limit to 100 records (optional)
    
    dying_records = convert_objectid_to_str(dying_records)
    
    if dying_records:
        return {"knitting_records": dying_records}
    else:
        raise HTTPException(status_code=404, detail="No yarn tracking records found in dying department")
@app.get("/trim/yarn/")
async def get_all_yarn_tracking():
    # Fetch all records from the knitting collection
    trim_records = await trim_collection.find().to_list(length=100)  # Limit to 100 records (optional)
    trim_records = convert_objectid_to_str(trim_records)
    
    if trim_records:
        return {"knitting_records": trim_records}
    else:
        raise HTTPException(status_code=404, detail="No yarn tracking records found in triming department")
@app.get("/admin/yarn/")
async def get_all_yarn_tracking():
    # Fetch all records from the knitting collection
    admin_records = await admin_collection.find().to_list(length=100)  # Limit to 100 records (optional)
    
    admin_records = convert_objectid_to_str(admin_records)
    
    if admin_records:
        return {"knitting_records": admin_records}
    else:
        raise HTTPException(status_code=404, detail="No yarn tracking records found in process")

# Endpoint to retrieve dying record for a specific PO number
@app.get("/download_po/{po_number}")
async def download_po(po_number: str):
    # Fetch the order from MongoDB
    order = await orders_collection.find_one({"po_number": po_number})
    
    if not order:
        raise HTTPException(status_code=404, detail="PO not found")
    
    # Convert ObjectId to string for JSON-friendly representation
    order["id"] = str(order["_id"])
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["Field", "Value"])
    
    # Write order details
    for key, value in order.items():
        # For labels list, convert to string
        if key == "labels" and value:
            labels_str = "; ".join([f"{label['vendor_id']}-{label['quality']}-{label['printed_woven']}" for label in value])
            writer.writerow([key, labels_str])
        elif key not in ["_id"]:
            writer.writerow([key, value])
    
    # Move pointer to start of the stream
    output.seek(0)
    
    # Return as downloadable CSV
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=PO_{po_number}.csv"}
    )
@app.get("/view_po/{po_number}", response_model=Order)
async def view_po_json(po_number: str):
    # Fetch the order from MongoDB using the PO number
    order = await orders_collection.find_one({"po_number": po_number})
    
    if not order:
        raise HTTPException(status_code=404, detail="PO not found")
    
    # Convert ObjectId to string for the response
    order["_id"] = str(order["_id"])
    
    return order

def generate_po_pdf(po_number: str, order: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    # Set up the title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, f"PO Number: {po_number}")

    # Add customer name, order number, etc.
    p.setFont("Helvetica", 12)
    p.drawString(100, 730, f"Customer Name: {order['customer_name']}")
    p.drawString(100, 710, f"Order Number: {order['order_number']}")
    p.drawString(100, 690, f"Company Order Number: {order['company_order_number']}")
    p.drawString(100, 670, f"Yarn Count: {order['yarn_count']}")
    p.drawString(100, 650, f"Content: {order['content']}")
    p.drawString(100, 630, f"Spun: {order['spun']}")
    p.drawString(100, 610, f"Sizes: {', '.join(order['sizes'])}")
    p.drawString(100, 590, f"Knitting Type: {order['knitting_type']}")
    p.drawString(100, 570, f"Dyeing Type: {order['dyeing_type']}")
    p.drawString(100, 550, f"Finishing Type: {order['finishing_type']}")
    
    # Labels Section: Format each label into a readable string
    if order['labels']:
        labels_str = []
        for label in order['labels']:
            label_info = f"Vendor ID: {label['vendor_id']}, Quality: {label['quality']}, Printed/Woven: {label['printed_woven']}"
            if 'elastic_type' in label:
                label_info += f", Elastic: {label['elastic_type']}"
            if 'elastic_vendor_id' in label and label['elastic_vendor_id']:
                label_info += f", Elastic Vendor ID: {label['elastic_vendor_id']}"
            labels_str.append(label_info)
        p.drawString(100, 530, f"Labels: {'; '.join(labels_str)}")

    # Finalize the PDF
    p.showPage()
    p.save()

    # Move the buffer position to the beginning of the file
    buffer.seek(0)

    return buffer

# Endpoint to download PO as PDF
@app.get("/download/{po_number}")
async def download_po(po_number: str):
    # Fetch the order from MongoDB using the PO number
    order = await orders_collection.find_one({"po_number": po_number})
    
    if not order:
        raise HTTPException(status_code=404, detail="PO not found")
    
    # Generate the PDF in memory
    pdf_buffer = generate_po_pdf(po_number, order)
    
    # Return the PDF as a downloadable response
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=PO_{po_number}.pdf"}
    )
@app.get("/view_all_po")
async def get_all_yarn_tracking():
    # Fetch all records from the knitting collection
    total_po = await orders_collection.find().to_list(length=100)  # Limit to 100 records (optional)
    
    total_po = convert_objectid_to_str(total_po)
    
    if total_po:
        return total_po
    else:
        raise HTTPException(status_code=404, detail="No yarn tracking records found")
