# OpenAI Health

- Source: `config/nodes.yaml`
- Mode: `mock`

| Node | OpenAI | ChatGPT | API | Latency ms | Categories | Error |
| --- | --- | --- | --- | ---: | --- | --- |
| JP-Direct-Tokyo | true | true | - | - | direct, japan | - |
| SG-Direct-Singapore | true | true | - | - | direct, singapore | - |
| US-Direct-LosAngeles | true | true | - | - | direct, united_states | - |
| HK-Dedicated-HongKong | false | false | - | - | dedicated, hong_kong | mock: not a direct JP/SG/US candidate |
| MO-Relay-Macau | false | false | - | - | macau, relay | mock: not a direct JP/SG/US candidate |
