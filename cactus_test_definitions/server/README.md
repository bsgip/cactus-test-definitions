
# Server Test Schema

This is for the **SERVER** test procedures.

At its most basic level, a server test is a series of actions by a virtual "client" that will probe the server and look for unexpected behaviour/responses.

## Clients and Context

Each test will define one or more "virtual clients" as a precondition. These can be restricted to a specific client type (eg Aggregator or Device) or left unspecified.

At the beginning of each test, the client will only know it's LFDI, PEN, PIN and certificate details. Through running actions it will discover resources and populate a local "context" which represents the last seen CSIP-Aus resources. Each client's context is seperate, so if Client A performs discovery, those resources will be invisible to Client B.

## Steps Schema

The most basic building block of a server `TestProcedure` is a `Step`. Each `Step` will always define a single `Action` which dictates the behaviour of a virtual client (eg sending a particular request) which is then followed by a series of `Check` objects to evaluate. In order for a step to pass it must:

1) Execute with any errors (eg - able to successfully make a HTTP request to the utility server)
2) Have all checks return passed


Steps:
  - id: DISCOVERY
    action: 
      type: discovery
      parameters:
        resources:
          - DeviceCapability
          - Time
          - MirrorUsagePointList
          - EndDevice
          - DER
    checks:
      - type: discovered
        parameters:
          resources:
            - DeviceCapability
            - Time
            - MirrorUsagePointList
            - EndDevice
            - DER
          links:
            - ConnectionPoint
            - Registration
            - DERCapability
            - DERSettings
            - DERStatus
      - type: end-device
        parameters:
          matches_client: true
      - type: time-synced


Step Schema:
```
Steps:
  - DESCRIPTIVE_TITLE_OF_STEP: # This is used for display
    action: # 
      type:  # string identifier of the action type - see table below
      parameters: # Any parameters to modify the default behaviour of the action - see table below
    checks: # A list of Check definitions that will need to be true for this event to trigger - see section on Checks below 
      - type:  # string identifier of the check type - see table below
        parameters: # Any parameters to modify the default behaviour of the check - see table below

    client: # The string descriptor of the "Required Client" in the preconditions that will execute this step 
            # (Defaults to the first required client)
    
    use_client_context: # The string descriptor of the "Required Client" in the preconditions whose context/memory
                        # of discovered resources will be used (for testing cross client authentication issues)
    instructions: # List of text strings to render while this test is executing
    repeat_until_pass: # Most steps if failed will abort the test, setting this to true will repeat this step regularly
                       # until a pass is recorded (eg - use it to prompt a server to inject a DERControl)
```


### Actions

These are the currently defined `Action` elements that can be included in a test.

This is an example of an `Action` elements that trigger a client to requests links from the device capability URI until all nominated resources are reached.

```
action: 
  type: discovery
  parameters:
  resources:
    - Time
    - MirrorUsagePointList
    - EndDevice
    - DER
```


| **name** | **params** | **description** |
| -------- | ---------- | --------------- |
| `discovery` | `resources: list[CSIPAusResource]` `next_polling_window: bool/None` | Performs a full discovery / refresh of the client's context from DeviceCapability downwards, looking to discover the specific resources. Can be delayed until the next polling window. |
| `notifications` | `sub_id: str` `collect: bool/None` `disable: bool/None` | `sub_id` must match a previously created subscription. If `collect`, consumes subscription notifications and inserts them into the current context, if `disable` causes the subscription notification webhook to simulate an outage (return HTTP 5XX) |
| `wait` | `duration_seconds: int` | Performs no action for the nominated period of time |
| `refresh-resource` | `resource: CSIPAusResource` `expect_rejection: bool/None` `expect_rejection_or_empty: bool/None` | Forces a particular resource to be refreshed (using existing hrefs in context). Can be set to expect a HTTP 4XX ErrorResponse and/or an empty list resource (if appropriate). |
| `insert-end-device` | `force_lfdi: str/None` `expect_rejection: bool/None` | Causes the client to submit a new EndDevice registration and resolves the returned Location header |
| `upsert-connection-point` | `connectionPointId: str` `expect_rejection: bool/None` | Causes the client to submit a new ConnectionPoint with ID for the client's EndDevice |
| `upsert-mup` | `mup_id: str` `location: CSIPAusReadingLocation` `reading_types: list[CSIPAusReadingType]` `mmr_mrids: list[str]/None` `pow10_multiplier: int/None`  `expect_rejection: bool/None` | Submits a MirrorUsagePoint with MirrorMeterReading's. Will ensure stable MRID values for the same sets of parameters (unless overridden with mmr_mrids). `mup_id` will alias this MirrorUsagePoint for future action calls. |
| `insert-readings` | `mup_id: str` `values: ReadingTypeValues` `expect_rejection: bool/None` | Begins the submission of readings (at MUP post rate, to an earlier call to `upsert-mup` with the same `mup_id`). Will interleave transmission with subsequent steps (non blocking) if multiple sets of values are specified |
| `upsert-der-status` | `genConnectStatus: int/None` `operationalModeStatus: int/None` `alarmStatus: int/None` `expect_rejection: bool/None` | Sends DERStatus - validates that the server persisted the values correctly |
| `upsert-der-capability` | `type: int` `rtgMaxW: int` `modesSupported: int` `doeModesSupported: int` | Sends DERCapability - validates that the server persisted the values correctly |
| `upsert-der-settings` | `setMaxW: int` `setGradW: int` `modesEnabled: int` `doeModesEnabled: int` | Sends DERSettings - validates that the server persisted the values correctly |
| `send-malformed-der-settings` | `updatedTime_missing: bool` `modesEnabled_int: bool`  | Sends a malformed DERSettings - expects a failure and that the server will NOT change anything |
| `send-malformed-response` | `mrid_unknown: bool` `endDeviceLFDI_unknown: bool` `response_invalid: bool`  | Sends a malformed Response (using the most recent DERControl replyTo) - expects a failure response |
| `create-subscription` | `sub_id: str` `resource: CSIPAusResource` | Sends a new Subscription - validates that the server persisted the values correctly via Location. `sub_id` will alias this subscription for future action calls. |
| `delete-subscription` | `sub_id: str` | Sends a deletion for a previously created Subscription. |
| `respond-der-controls` | None | Enumerates all known DERControls and sends a Response for any that require it. |


### Checks

A `Check` is a boolean test of what the client has in its current context. They are typically defined as a success/failure condition to be run at the end of a `Step`.

| **name** | **params** | **description** |
| -------- | ---------- | --------------- |
| `discovered` | `resources: list[CSIPAusResource]` `links: list[CSIPAusResource]` | Does the client's context have the nominated resources (or the parent resource with an appropriate link). |
| `time-sync` | None | Does the client have a TimeResponse and does it closely map to the client's local time. |
| `function-set-assignment` | `minimum_count: int/None` `maximum_count: int/None` `matches_client_edev: bool/None` | Are there the correct number of FunctionSetAssignments that may or may not belong solely under the client's EndDevice (or any accessible EndDevice) |
| `end-device-list` | `matches_poll_rate: int` | Is there an EndDeviceList that has the specified pollRate |
| `end-device` | `matches_client: bool` `matches_pin` | Is there an EndDevice that matches the client's LFDI (can be negatively asserted) and does it have a specific Registration PIN |
| `der-program` | `minimum_count: int/None` `maximum_count: int/None` `primacy: int/None` `fsa_index: int/None` | Are there enough DERProgram(s) that satisfy the filter criteria? `fsa_index` matches DERPrograms that belong to the nth (0 based) FunctionSetAssignment |
| `der-control` | `minimum_count: int/None` `maximum_count: int/None` `latest: bool/None` `opModImpLimW: float/None` `opModExpLimW: float/None` `opModLoadLimW: float/None` `opModGenLimW: float/None` `opModEnergize: bool/None` `opModConnect: bool/None` `opModFixedW: float/None` `rampTms: int/None` `randomizeStart: int/None` `event_status: int/None` `responseRequired: int/None` `derp_primacy: int/None` | Are there enough DERProgram(s) that satisfy the filter criteria? `latest` will ONLY match the most recent DERControl. |
| `default-der-control` | `opModExpLimW: float/None` `opModLoadLimW: float/None` `opModGenLimW: float/None` `setGradW: int/None` |  matches any DefaultDERControl with the specified values |
| `mirror-usage-point` | `matches: bool` `location: CSIPAusReadingLocation/None` `reading_types: list[CSIPAusReadingType]/None` `mmr_mrids: list[str]/None` `post_rate_seconds: int/None` | Does a MirrorUsagePoint exist with the specified values (or not exist if `matches` is false). Only asserts specified values. |
| `subscription` | `matches: bool` `resource: CSIPAusResource`| Does a Subscription exist for the specified resource (or not exist if `matches` is false). |
| `poll-rate` | `resource: CSIPAusResource` `poll_rate_seconds: int` | Does the nominated resource have the specified poll rate. |


### Parameter Variable Resolution

Any `parameter` element expects a series of name/value pairs to pass to the "parent" `Action` or `Check` . For example:

```
parameters:
    number_param: 123
    text_param: Text Content
    date_param: 2020-01-02 03:04:05Z
    csip_aus_resource: EndDeviceList

```

But placeholder variables may also be used to reference things that aren't known until the test is underway. For example, the following would instead set `number_param` to the current setMaxW supplied by the client while `date_param` would be set to the moment in time that the `Action`, `Check` or `Event` is being evaluated.

```
parameters:
    number_param: $setMaxW
    text_param: Text Content
    date_param: $now

```

The following are all the `NamedVariable` types currently implemented (these are distinct from the named variables
defined in the client test procedures)

| **name** | **description** |
| -------- | --------------- |
| `$now` | Resolves to the current moment in time (timezone aware). Returns a datetime |
| `$setMaxW` | Resolves to the current client configuration value for `DERSetting.setMaxW` as a number. |


Expressions are also supported.

```
parameters:
    number_param: $(setMaxW / 2)
    text_param: Text Content
    date_param: $(now - '5 mins')
```
