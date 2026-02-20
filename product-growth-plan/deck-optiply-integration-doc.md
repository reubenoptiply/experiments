# Deck x Optiply Jobs

| Job Code | Job Type/Scope | Purpose | Input | Webhook returns |
| ----- | :---: | ----- | ----- | ----- |
| [EnsureConnection](#bookmark=id.1e4938mcgo4w) | **Write**(Inject fields) | Authenticate with the external service and obtain an access token.  | Username Password Source GUID | Access token |
| [AddItemsToCart](#additemstocart) | **Write** (Trigger action) | Add items to a cart on shopping portals. | Access token Array of: SKU Quantity Expected price | Success Message Array of: SKU Status In stock amount Price Price comparison Added to cart |
| [CloseConnection](#bookmark=id.r5j32xqbwmw6) | **Write**(Trigger action) | End the session with the external service. | Access token |  |

## 

## NOTES ABOUT THE ENDPOINT

The main endpoint that will be called is /api/v1/jobs/submit.  
This endpoint will allow you to submit a job. When calling the endpoint through our API, the results of the job are delivered via webhooks.

To use the API, you'll need to choose a Job Code according to your needs (see table on page 1). For example, if you are trying to make a connection to a source, you would use the Job Code "EnsureConnection". If you are trying to get the information for a user booking, you would use the Job Code "FetchUserBookingInfo".

You will then need to provide the request parameters required for the endpoint to do its work. This input is different for every type of Job you are trying to accomplish. For example, you will need to enter the time period you want data from when fetching the user bookings.

Once all the parameters are filled-in, the endpoint will do the rest\!

**IMPORTANT:** If you try to perform a Job while another one is already in progress on the same account, it will be **automatically blocked**, and an error message will be displayed with the Job\_Id that is already running.

In this case, the endpoint will return a 409 response that looks like this:

```
{
   "job_guid": "b35aa2af-41e4-4833-95c9-9efd2069e70c",
   "error_message": "Job b35aa2af-41e4-4833-95c9-9efd2069e70c is already running"
}
```

**EXCEPTION:** There is one exception to the above rule, and it lies with EnsureConnection.  
If you try to call a new EnsureConnection while one is already active, the endpoint will return a 400 response that looks like this:

```
{
   "error_message": "An active connection exists. EnsureConnection cannot be called.",   "error_code": "ACTIVE_CONNECTION_EXISTS"
}
```

### EnsureConnection

```
curl --location 'https://live.deck.co/api/v1/jobs/submit' \	// Choose whether you want to call live.deck.co or sandbox.deck.co
--header 'x-deck-client-id: <insert client_id>' \          	// Insert your Deck client_id
--header 'x-deck-secret: <insert secret>' \			// Insert your Deck secret (sanbox secret for sandbox, dev for live)
--header 'Content-Type: application/json' \
--data '{
  "job_code": "EnsureConnection",
  "input": {
    "username": "<type username>",				// Input username
    "password": "<type password>",				// Input password
    "source_guid": "<insert GUID for the source>"		// Input guid for the source
  }
}
```

Example of a successful webhook that would be sent to you

```
{
  "job_guid": "b35aa2af-41e4-4833-95c9-9efd2069e70c",
  "output": {
    "access_token": "access-production-3a0c2c5b-110a-4837-c695-08dd4c38076f"
  },
  "webhook_type": "Job",
  "webhook_code": "EnsureConnection",
  "environment": "Production"
}
```

Example of a webhook that would be sent to you in case of error

```
{
  "job_guid": "b35aa2af-41e4-4833-95c9-9efd2069e70c",
  "error": {
    "error_code": "INVALID_CREDENTIALS",
    "error_message": "The provided credentials were incorrect"
  },
  "webhook_type": "Job",
  "webhook_code": "Error",
  "environment": "Production"
}
```

In case of MFA, you will receive the following webhook event

```
{
  "job_guid": "1ccb06176-550c-6574-8364-8hbgg94ldk909"
  "question": "Enter your MFA code"
  "webhook_type": "Job"
  "webhook_code": "MfaRequired"
  "environment": "Production"
}
```

You must then call the **jobs/mfa/answer** endpoint with the following body

```
{
  "job_guid": "1ccb06176-550c-6574-8364-8hbgg94ldk909"
  "answer": "code"
}
```

### AddItemsToCart {#additemstocart}

```
curl --location 'https://live.deck.co/api/v1/jobs/submit' \	// Choose whether you want to call live.deck.co or sandbox.deck.co
--header 'x-deck-client-id: <insert client_id>' \          	// Insert your Deck client_id
--header 'x-deck-secret: <insert secret>' \			// Insert your Deck secret (sanbox secret for sandbox, dev for live)
--header 'Content-Type: application/json' \
--data '{
  "job_code": "AddItemsToCart",
  "input": {
    "access_token": "<insert access token>",		// Input the access token received from the EnsureConnection webhook
    "items": [
      {
        "sku": "<insert value>",				// Input the SKU of the item
        "quantity": <insert value>,			// Input the quantity you want to buy
        "expected_price": "<insert value>"		// Input the expected price of the item (including the currency mark)
      }
    ] 
  }
}
```

Example of a successful webhook that would be sent to you

```
{
  "job_guid": "b35aa2af-41e4-4833-95c9-9efd2069e70c",
  "output": {
    "success": true,
    "items": [
       {
         "sku": "6468634324",
         "status": "In stock",				// One of: "In stock", "Out of stock", "Product not found"
         "price": "€10.99",
         "price_is": "Higher than expected",		// One of: "As expected", "Lower than expected", "Higher than expected"
         "added_to_cart": true
       },
       {
         "sku": "AH7687",
         "status": "Out of stock",
         "added_to_cart": false
       }
    ]
  },
  "webhook_type": "Job",
  "webhook_code": "AddItemsToCart",
  "environment": "Production"
}
```

Example of a webhook that would be sent to you in case of error

```
{
  "job_guid": "b35aa2af-41e4-4833-95c9-9efd2069e70c",
  "output": {
    "success": false,
    "message": "Invalid inputs."
  },
  "webhook_type": "Job",
  "webhook_code": "AddItemsToCart",
  "environment": "Production"
}
```

### 

### CloseConnection

```
curl --location 'https://live.deck.co/api/v1/jobs/submit' \	// Choose whether you want to call live.deck.co or sandbox.deck.co
--header 'x-deck-client-id: <insert client_id>' \          	// Insert your Deck client_id
--header 'x-deck-secret: <insert secret>' \			// Insert your Deck secret (sanbox secret for sandbox, dev for live)
--header 'Content-Type: application/json' \
--data '{
  "job_code": "CloseConnection",
  "input": {
  "access_token": "<insert access token>"			// Input the access token received from the EnsureConnection webhook
	}
}
```

No webhook is returned.

