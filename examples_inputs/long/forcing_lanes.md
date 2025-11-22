**Process name:** `Order_and_Fulfilment_TwoLanes`
**Pool:** `participant_company` (id: `participant_company`, name: `Company`)
**Lanes inside pool:**

* `lane_sales` (id: `lane_sales`, name: `Sales`)
* `lane_logistics` (id: `lane_logistics`, name: `Logistics`)

**Purpose:** Internal company process where Sales handles customer interaction and Logistics handles fulfillment.

**Flow (sequence with IDs & types):**

1. **Start (Sales lane)**

   * `start_sales` — StartEvent in `lane_sales`.

2. **Receive Customer Order (Sales Task)**

   * `task_salesReceiveOrder` — Task: "Receive Customer Order"
   * DataObject `order_doc`.

3. **Check Inventory (Logistics Task)**

   * Message/sequence flow to `task_checkInventory` in `lane_logistics`.
   * `task_checkInventory` — Task: "Check Inventory"
   * Gateway `gateway_stock` (Exclusive):

     * If in stock → `task_reserveStock`
     * If out of stock → `task_notifySalesBackorder`

4. **Reserve Stock (Logistics Task)**

   * `task_reserveStock` — Task: "Reserve Stock"
   * Send message/sequence to `task_confirmOrderSales` in `lane_sales`.

5. **Confirm Order to Customer (Sales Task)**

   * `task_confirmOrderSales` — Task: "Confirm Order to Customer"
   * End `end_confirmed`.

6. **Prepare Shipment (Logistics Task)**

   * `task_prepareShipment` — Task: "Prepare Shipment"

7. **Dispatch (Logistics Task)**

   * `task_dispatch` — Task: "Dispatch"
   * Message/sequence `sequence_dispatch_notice` back to Sales: `task_updateShippingStatus`.

8. **Update Shipping Status (Sales Task)**

   * `task_updateShippingStatus` — Task: "Update Shipping Status"
   * `task_notifyCustomerDelivery` — Task: "Notify Customer Delivery"

9. **Invoice & Payment (Sales Task)**

   * `task_createInvoice` — Task: "Create Invoice"
   * `task_receivePayment` — Task: "Receive Payment"
   * Gateway `gateway_payment` (Exclusive):

     * If payment received → `task_closeOrder` (End)
     * If payment failed → `task_handlePaymentFailure` (escalation)

10. **End**

    * `end_completed` — EndEvent.

**Special elements / conditions:**

* `gateway_stock` checks inventory boolean `in_stock`.
* Include message flows only if external third-parties are involved. For pure internal lanes, use sequence flows between lanes.
* Add a boundary timer `timer_backorder` on `task_notifySalesBackorder` that triggers a `task_orderSupplier` in Logistics if backorder persists for 7 days.

