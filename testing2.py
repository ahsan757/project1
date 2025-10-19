from fastapi import FastAPI, Request
import json

app = FastAPI()

@app.post("/event")
async def receive_event(request: Request):
    try:
        data = await request.json()
        event = data.get("data", {}).get("AccessControllerEvent", {})

        name = event.get("name", "Unknown")
        event_type = event.get("eventDescription", "").lower()
        major_type = event.get("majorEventType", None)
        sub_type = event.get("subEventType", None)

        # Only log when actual login (face/card/fingerprint verified)
        if major_type == 5 and sub_type in [75, 74, 71, 1]:  
            # these subtypes correspond to "Verified success" events
            print(f"✅ Login detected: {name}")
        else:
            # ignore all other events (door open, ping, etc.)
            pass

    except Exception as e:
        # In case of malformed data or XML fallback
        print("⚠️ Non-JSON or unknown event ignored")
        return {"status": "ignored", "error": str(e)}

    return {"status": "ok"}
