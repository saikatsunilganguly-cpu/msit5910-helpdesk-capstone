# Non-Functional Requirements

| ID   | Non-Functional Requirement | Design Implication |
|------|------------------------------|----------------------|
| NFR1 | Usability: non-technical users should be able to submit and categorise a ticket without specialist knowledge. | Plain-language prompts, minimal fields, and guided choices. |
| NFR2 | Reliability: workflow decisions should be applied consistently for equivalent tickets. | Standard categories, a priority matrix, and defined routing rules. |
| NFR3 | Scalability: additional categories or queues should be added without redesigning the workflow. | Configurable category and routing lookup tables. |
| NFR4 | Security: ticket data should be protected from unauthorised access or inappropriate disclosure. | RBAC, encryption, audit logging, retention controls, and least privilege. |
| NFR5 | Transparency and fairness: decision prompts should be understandable and applied consistently. | Explainable category prompts and documented escalation rules. |
| NFR6 | Performance: the process should reduce avoidable initial-triage effort. | Fewer unclear choices and predefined routing paths. |
