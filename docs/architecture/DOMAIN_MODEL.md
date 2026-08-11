# Generic Domain Model

The platform model is organized around these generic entities:

```text
Organization -> Department -> OrganizationMember -> Agent
                         -> Profession -> Role -> Responsibility
Project -> Task -> WorkflowDefinition -> WorkflowStep
Task -> Artifact -> ArtifactRevision -> Evidence -> Review -> Finding
Agent -> Skill -> Knowledge -> Experience -> Qualification
Agent -> Tool -> Provider -> Runtime
LearningSource -> Knowledge/Skill updates (only after review)
```

Identity and work are separate. An `Agent` is an employee identity. A provider
is an execution adapter. A `Task` is the unit of intent and an `AgentRun` is one
execution attempt. An organization is a management structure; it is not a list
of chat participants.

Existing Roman/Petr profiles, tasks, runs, skills and PCB data remain valid.
The universal tables are additive and use stable IDs, nullable links where a
template is not yet instantiated, and non-destructive initialization.
