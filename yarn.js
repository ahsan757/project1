// yarn.js - API functions for interacting with the backend

const apiUrl = 'http://127.0.0.1:8000'; // FastAPI URL

const postData = async (endpoint, data) => {
    try {
        const response = await fetch(`${apiUrl}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
};

const putData = async (endpoint, data) => {
    try {
        const response = await fetch(`${apiUrl}${endpoint}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
};

// Vendor registration
document.getElementById('vendor-form')?.addEventListener('submit', async function (e) {
    e.preventDefault();

    const companyName = document.getElementById('company-name').value;
    const brokerName = document.getElementById('broker-name').value;
    const contractType = document.getElementById('contract-type').value;
    const contact = document.getElementById('contact').value;
    const gstNumber = document.getElementById('gst-number').value;
    const prefix = document.getElementById('prefix').value;

    const vendorData = { company_name: companyName, broker_name: brokerName, contract_type: contractType, contact, gst_number: gstNumber, prefix };

    try {
        const result = await postData('/register_vendor/', vendorData);
        document.getElementById('vendor-message').textContent = `Vendor registered with ID: ${result.vendor_id}`;
    } catch (error) {
        document.getElementById('vendor-message').textContent = 'Error registering vendor';
    }
});

// Yarn Request
document.getElementById('request-form')?.addEventListener('submit', async function (e) {
    e.preventDefault();

    const count = document.getElementById('count').value;
    const content = document.getElementById('content').value;
    const spunType = document.getElementById('spun-type').value;
    const bags = document.getElementById('bags').value;
    const kgs = document.getElementById('kgs').value;

    const requestData = { count: parseInt(count), content, spun_type: spunType, bags: parseInt(bags), kgs: parseFloat(kgs) };

    try {
        const result = await postData('/request_yarn/', requestData);
        document.getElementById('request-message').textContent = `Yarn requested successfully. Request ID: ${result.request_id}`;
    } catch (error) {
        document.getElementById('request-message').textContent = 'Error requesting yarn';
    }
});

// Yarn Receive
document.getElementById('receive-form')?.addEventListener('submit', async function (e) {
    e.preventDefault();

    const vendorId = document.getElementById('vendor-id').value;
    const spunType = document.getElementById('spun-type-receive').value;
    const kgsReceived = document.getElementById('kgs-received').value;
    const receivedDate = document.getElementById('received-date').value;

    const receiveData = { vendor_id: vendorId, spun_type: spunType, kgs_received: parseFloat(kgsReceived), received_date: receivedDate };

    try {
        const result = await putData('/receive_yarn/', receiveData);
        document.getElementById('receive-message').textContent = `Yarn received successfully. Remaining KGs: ${result.remaining_kgs}`;
    } catch (error) {
        document.getElementById('receive-message').textContent = 'Error receiving yarn';
    }
});
