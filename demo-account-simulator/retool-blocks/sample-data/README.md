# Sample data

**bos-created.json** — Reference copy of the request bodies used to create buy orders (POST /v1/buyOrders). Each item is the payload that was sent; it does **not** include the API-assigned `id` returned in the create response.

To **patch `completed`** on these BOs you need each BO’s `id`. Either:

1. Use the **create Loop’s response array** in Retool (each element should have `data.id` and `data.attributes.expectedDeliveryDate`), and point **build_patch_completed_bodies** at that block, or  
2. **GET** buy orders for the account from the API, then use that list (with `id` and `expectedDeliveryDate`) as the input to **build_patch_completed_bodies**, or pass the array of ids as `bo_ids_in_order` in the same order as the items in this file.

See [build_patch_completed_bodies.js](../build_patch_completed_bodies.js) and the main [README](../README.md).
