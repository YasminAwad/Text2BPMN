**Process name:** `Order_and_Fulfilment_TwoPools`
**Pools/Participants:**

* `Participant_Customer` (id: `participant_customer`, name: `Customer`)
* `Participant_supplier` (id: `participant_supplier`, name: `Supplier`)

**Purpose:** Customer places an order; Supplier validates, accepts, ships, and sends invoice. Customer pays and confirms receipt.

**Flow (sequence with IDs & types):**

1. **Start (Customer)**

   * `start_customer` — StartEvent in `participant_customer`.

2. **Place Order (Customer Task)**

   * `task_placeOrder` — Task: "Place Order"
   * Output: DataObject `order_doc`.

3. **Send Order (Message)**

   * Message Flow `msg_order_to_supplier`: from `task_placeOrder` to `task_receiveOrder` in Supplier.

4. **Receive Order (Supplier Task)**

   * `task_receiveOrder` — Task in `participant_supplier`: "Receive Order". Input: `order_doc`.

5. **Validate Order (Supplier Task)**

   * `task_validateOrder` — Task: "Validate Order"
   * Gateway `gateway_validation` (Exclusive):

     * If valid → `task_prepareShipment`
     * If invalid → `task_rejectOrder`

6. **Reject Order (Supplier Task + Message)**

   * `task_rejectOrder` — Task: "Reject Order"
   * Send message `msg_rejection` back to Customer to `task_receiveRejection`.

7. **Receive Rejection (Customer Task)**

   * `task_receiveRejection` — Task: "Receive Rejection"
   * End `end_rejected` — EndEvent.

8. **Prepare Shipment (Supplier Task)**

   * `task_prepareShipment` — Task: "Prepare Shipment"

9. **Ship Goods (Supplier Task + Message)**

   * `task_shipGoods` — Task: "Ship Goods"
   * Message Flow `msg_shipment_notice`: Supplier → Customer `task_receiveShipmentNotice`.

10. **Receive Shipment Notice (Customer Task)**

    * `task_receiveShipmentNotice` — Task: "Receive Shipment Notice"

11. **Confirm Delivery (Customer Task)**

    * `task_confirmDelivery` — Task: "Confirm Delivery"
    * Message `msg_confirmation` from Customer → Supplier `task_receiveConfirmation`.

12. **Receive Confirmation & Create Invoice (Supplier Task)**

    * `task_receiveConfirmation` — Task: "Receive Confirmation"
    * `task_createInvoice` — Task: "Create Invoice"
    * Message Flow `msg_invoice` from Supplier → Customer `task_receiveInvoice`.

13. **Receive Invoice & Pay (Customer Task)**

    * `task_receiveInvoice` — Task: "Receive Invoice"
    * `task_payInvoice` — Task: "Pay Invoice"
    * Message Flow `msg_payment` from Customer → Supplier `task_receivePayment`.

14. **Receive Payment & Close Order (Supplier Tasks)**

    * `task_receivePayment` — Task: "Receive Payment"
    * `task_closeOrder` — Task: "Close Order"
    * `end_success` — EndEvent in both pools indicating process completion.

**Special elements / conditions:**

* Validation gateway `gateway_validation` is exclusive (conditions: `valid == true` or `valid == false`).
* Optional timer: If payment not received within 14 days, Supplier triggers `timer_paymentReminder` (TimerEvent attached to `task_createInvoice`) sending `msg_paymentReminder`. (Include if you want a boundary timer.)