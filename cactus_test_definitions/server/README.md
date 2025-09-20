
cactus config server dcap https://foo.bar/dcap

cactus config client client1 certificate -f cert.pem
cactus config client client1 key -f cert.key
cactus config client client1 type aggregator|device
cactus config client client1 lfdi ABC123
cactus config client client1 sfdi 456789
cactus config client client1 pen 456789
cactus config client client1 pin 123456
cactus config client client1 maxW 6000
cactus config client client1 notificationuri https://localhost:1234/foo/bar

cactus test run --report "output.pdf" --version v1.2  S-ALL-01 client1
cactus test list

```
Description: Discovery with out of band registration
Category: Registration
Classes:
 - A
 - CP
 - R
 - DRED

TargetVersions:
 - v1.2    

preconditions:
    clients:
        - client_name: device

steps: 
   []

```

# S-ALL-01

steps: 
    -   name: DISCOVERY
        clients:
            - client1
        action: discovery
        checks:
            - type: discovered-links
              parameters:
                links:
                    - ConnectionPointLink
                        RegistrationLink
                        DERListLink
                        Time
                        DERList
                        DERSettings
                        DERCapability
                        DERStatus
                        MUPLink
            - has-end-device
                parameters:
                    matches-client: true
            - time-synced

# S-ALL-02


steps: 
    -   name: DISCOVERY
        action: discovery
        checks:
            - type: discovered-links
              parameters:
                links:
                    - ConnectionPointLink
                        RegistrationLink
                        DERListLink
                        Time
                        MUPLink
            - has-end-device
                parameters:
                    matches-client: false
            - time-synced
        
    - name: REGISTER
      action: register-end-device
        parameters:
            resolve-location-header: true
      checks:
         - has-end-device
                parameters:
                    matches-client: true
        - type: discovered-links
              parameters:
                links:
                    - ConnectionPointLink
                      RegistrationLink
                      DERListLink
                      Time
                      MUPLink
                    
    - name: WAIT-FOR-DER-LIST
      action: discovery
        parameters:
            wait_for_resources: 
                - DERSettingsLink
                - DERCapabilityLink
                - DERStatusLink
    checks:
         - has-end-device
                parameters:
                    matches-client: true
            

            
    -
# S-OPT-01

steps: 
    -   name: DISCOVERY
        action: discovery
        checks:
            - type: discovered-links
                parameters:
                links:
                    - ConnectionPointLink
                    - RegistrationLink
                    - DERListLink
                    - Time
                    - MUPLink
            - has-end-device
                parameters:
                    matches-client: true # Should be pre-registered
        
    - name: REGISTER
      action: register-end-device
        parameters:
			expected_error_status_code: 4**
            resolve-location-header: true
      checks:
         - has-end-device
        	parameters:
            	matches-client: true
                    
            
    
# S-OPT-02

