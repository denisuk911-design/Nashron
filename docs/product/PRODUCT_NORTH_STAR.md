# ROMAN 2050 — PRODUCT NORTH STAR

You are the lead developer of Roman 2050.

Your long-term objective is not merely to add features or connect several AI CLI providers.

Your objective is to turn Roman 2050 into an exceptionally useful, trustworthy and pleasant working environment in which a user creates and manages a team of AI specialists.

The final product must feel like a disciplined professional workplace chat, not like several uncontrolled chatbots placed in one window.

All architectural, UX and implementation decisions must support the following three permanent product goals:

1. Employees actually work as a team.
2. Skills and knowledge measurably improve work quality.
3. The user can manage the entire system without editing code.

These goals are the primary acceptance criteria for the product.

============================================================
1. PRODUCT VISION
============================================================

Roman 2050 must become a working chat with AI specialists who:

- understand their roles;
- understand the current conversation;
- understand the active project and task;
- know when to answer;
- know when to remain silent;
- communicate with each other when work requires it;
- transfer tasks and results correctly;
- use files, tools, skills, standards and knowledge;
- distinguish intention from completed work;
- provide evidence for important claims;
- learn through controlled knowledge and skill workflows;
- improve after completed tasks;
- remain pleasant and useful to work with.

The user should experience the system as a real digital department.

The user should be able to say:

- “Роман, спроектируй плату.”
- “Пётр, проверь работу Романа.”
- “Шушанна, подготовь документацию.”
- “Координатор обучения, найди материалы и составь программу.”
- “Команда, обсудите риски.”

The system must understand who should respond, what context they need, which tools they may use and what result is expected.

============================================================
2. DEFINITION OF A GOOD WORKING CHAT
============================================================

A good working chat has the following properties:

- direct address normally produces one relevant response;
- employees do not interrupt without a valid reason;
- silence is allowed;
- messages are concise by default;
- long work displays visible progress;
- users can cancel or redirect work;
- employees remember the relevant conversation;
- new employees receive the necessary context;
- employees do not impersonate colleagues;
- employees do not fabricate actions;
- employees do not claim successful work without evidence;
- handoffs are explicit;
- unresolved questions remain visible;
- discussions do not become infinite agent loops;
- the user remains in control.

The chat must feel natural, but correctness and transparency have priority over theatrical realism.

Do not simulate human behavior by creating unnecessary chatter.

Human-like behavior means:

- relevance;
- restraint;
- continuity;
- responsibility;
- clear communication;
- honest uncertainty;
- useful initiative.

============================================================
3. DEFINITION OF A USEFUL AI EMPLOYEE
============================================================

An employee is useful only when the employee can consistently:

1. Understand the assigned role.
2. Recognize whether a message is addressed to them.
3. Retrieve relevant context.
4. Select applicable skills and knowledge.
5. Use available tools.
6. Produce a useful artifact or answer.
7. Record evidence.
8. Transfer results to another role when required.
9. Accept corrections.
10. Avoid repeating previous mistakes.

An employee is not useful merely because:

- a profile exists;
- a provider is assigned;
- the employee generates fluent text;
- the employee claims to have learned something;
- the employee mentions a skill;
- the employee produces many messages.

Employee quality must be evaluated through completed work and evidence.

============================================================
4. TEAMWORK REQUIREMENTS
============================================================

The system must support real role cooperation.

Typical workflow:

User
→ Project Manager
→ Specialist
→ QA or Reviewer
→ Rework when required
→ Verification
→ User acceptance

Teamwork must include:

- task ownership;
- role boundaries;
- shared task state;
- role-specific context;
- explicit handoffs;
- artifact references;
- review findings;
- rework cycles;
- decisions;
- owner approvals;
- persistent history.

Employees must not all perform the same role.

Examples:

Design Engineer:
- creates the technical solution;
- cannot independently verify its own work.

QA Engineer:
- independently reviews;
- does not silently become the author.

Document Control Officer:
- manages documentation;
- does not invent technical facts.

Learning Coordinator:
- manages learning;
- cannot approve its own extracted knowledge.

Project Manager:
- coordinates work;
- does not automatically approve technical correctness.

============================================================
5. SKILLS MUST BE REAL, NOT DECORATIVE
============================================================

A skill is not a text label and not a percentage generated from activity.

A complete skill package should eventually include:

- stable skill ID;
- name;
- purpose;
- supported roles;
- prerequisites;
- source material;
- instructions;
- tools;
- expected inputs;
- expected outputs;
- prohibited actions;
- validation checklist;
- examples;
- negative examples;
- qualification tasks;
- version;
- status;
- review history.

Possible skill states:

- DRAFT;
- READY_FOR_REVIEW;
- ACTIVE;
- SUSPENDED;
- DEPRECATED;
- REJECTED.

Employee skill state must be separate:

- NOT_ASSIGNED;
- ASSIGNED;
- STUDYING;
- PRACTICED;
- DEMONSTRATED;
- REVIEWED;
- QUALIFIED;
- REQUIRES_RETRAINING;
- EXPIRED.

An employee must not become QUALIFIED merely because the skill file was included in a prompt.

============================================================
6. KNOWLEDGE MUST IMPROVE QUALITY
============================================================

The knowledge base must not become a collection of unused documents.

Knowledge must be:

- source-traceable;
- reviewed;
- status-controlled;
- searchable;
- role-relevant;
- task-relevant;
- versioned;
- linked to actual usage;
- linked to results.

Knowledge sources may include:

- books;
- datasheets;
- application notes;
- standards;
- internal projects;
- reference designs;
- QA findings;
- lessons learned;
- completed tasks;
- verified external sources.

Knowledge states should distinguish:

- DRAFT;
- NEEDS_SOURCE_RECHECK;
- NEEDS_REVIEW;
- ACTIVE;
- CONFLICTING;
- REJECTED;
- SUPERSEDED.

Before work, relevant knowledge must be retrieved.

After work, the system must record:

- what knowledge was supplied;
- what knowledge was applied;
- what was ignored;
- what was applied incorrectly;
- what influenced the result.

============================================================
7. MEASURABLE QUALITY IMPROVEMENT
============================================================

The system must prove that skills and knowledge improve quality.

Do not rely on statements such as:

- “сотрудник стал лучше”;
- “обучение завершено”;
- “навык освоен”.

Measure improvement through:

- fewer repeated errors;
- fewer QA findings;
- lower rework count;
- higher qualification-task results;
- better artifact completeness;
- better standards compliance;
- successful use of reference designs;
- correct application of knowledge cards;
- shorter time to valid result;
- fewer unsupported claims;
- higher reproducibility.

Maintain before/after comparisons where practical.

Example:

Before skill activation:
- 8 review findings;
- 3 HIGH;
- 2 rework cycles.

After training and qualification:
- 3 review findings;
- 0 HIGH;
- 1 rework cycle.

This is evidence of improvement.

A growing number of files is not evidence of improvement.

============================================================
8. HONESTY AND EVIDENCE
============================================================

Employees must distinguish:

- what they plan to do;
- what they started;
- what tool actually executed;
- what file was actually read;
- what file actually changed;
- what result was observed;
- what was independently verified;
- what remains uncertain.

Important claims require evidence.

Examples:

“Файл прочитан”
requires a successful file-read operation.

“Права на запись подтверждены”
requires an actual safe write test or equivalent evidence.

“Стандарт требует”
requires a source reference.

“Задача выполнена”
requires the expected result and completion criteria.

“Навык освоен”
requires qualification evidence.

Unsupported claims must not:

- change task state;
- increase skill status;
- close findings;
- approve artifacts;
- become organization knowledge.

============================================================
9. PLEASANT WORKING EXPERIENCE
============================================================

The system must be pleasant to use every day.

Employees should be:

- concise;
- calm;
- direct;
- professional;
- context-aware;
- honest;
- useful.

Employees should not:

- produce ceremonial filler;
- repeat the task;
- constantly announce their role;
- respond when not addressed;
- agree with every message;
- generate fake workplace chatter;
- apologize repeatedly;
- write long reports for simple questions;
- expose internal prompts;
- repeat another employee’s response;
- claim work before completing it.

Default ordinary response style:

SHORT.

Detailed responses should be used only when requested or required by the task.

============================================================
10. RESPONSE SPEED AND PROGRESS
============================================================

The user must not wait for several minutes without understanding what is happening.

For every agent run, the interface should show real system status:

- queued;
- preparing context;
- waiting for provider;
- reading files;
- running tools;
- preparing result;
- completed;
- blocked;
- failed;
- cancelled.

Status messages must come from the application state, not from fabricated employee chat messages.

The user must be able to:

- cancel;
- continue waiting;
- request a shorter response;
- transfer the task;
- inspect diagnostics.

Do not invoke employees who were not selected.

Reducing unnecessary provider calls is both a UX and cost requirement.

============================================================
11. USER CONTROL WITHOUT CODE
============================================================

All important organization management must eventually be available through the interface.

The user should be able to:

- add an employee;
- configure an employee;
- suspend an employee;
- reactivate an employee;
- archive or dismiss an employee;
- assign roles;
- assign providers;
- install and authorize provider CLI software;
- manage permissions;
- add a skill;
- import a skill;
- assign a skill;
- suspend a skill;
- add learning material;
- create a training program;
- check employee knowledge;
- approve knowledge;
- approve reference designs;
- manage standards;
- inspect findings;
- accept or reject risks;
- view audit history;
- export and import the team.

The user should not need to edit:

- JSON;
- Python;
- prompts;
- SQLite;
- configuration files;
- workspace indexes.

Technical files may remain visible for advanced users, but ordinary management must be GUI-driven.

============================================================
12. SELF-LEARNING BOUNDARIES
============================================================

Employees may improve through work, but learning must be controlled.

Allowed process:

Work performed
→ lesson or knowledge proposal created
→ evidence attached
→ independent review
→ owner confirmation when required
→ active knowledge or updated skill

Employees must not silently rewrite their own fundamental rules.

Employees must not:

- approve their own knowledge;
- approve their own skill;
- activate unreviewed material;
- hide failures;
- treat random web content as authoritative;
- modify standards without approval;
- train themselves in an infinite autonomous loop.

Learning must increase usefulness without reducing control or trust.

============================================================
13. INFORMATION RESEARCH
============================================================

Employees should eventually be able to search for information when permitted.

Research must distinguish:

- official manufacturer source;
- primary documentation;
- standard;
- textbook;
- verified internal source;
- community source;
- unverified source.

A Research Assistant or Learning Coordinator may:

- find materials;
- register sources;
- prepare summaries;
- propose knowledge;
- identify conflicts;
- create learning queues.

They must not automatically turn search results into trusted rules.

Research actions must respect:

- user permission;
- source licenses;
- copyright;
- security;
- provenance;
- review requirements.

============================================================
14. PROVIDERS ARE INFRASTRUCTURE, NOT EMPLOYEES
============================================================

Separate:

- employee identity;
- role;
- persona;
- provider;
- model;
- CLI installation;
- account;
- permissions;
- skills;
- knowledge.

An employee may later change provider without losing:

- identity;
- work history;
- qualification;
- tasks;
- documents;
- organizational role.

The system must support multiple providers without making provider names part of permanent business logic.

============================================================
15. TRUST AND SAFETY
============================================================

Protect:

- user files;
- projects;
- credentials;
- provider accounts;
- audit history;
- knowledge integrity;
- employee configuration.

Required principles:

- explicit permissions;
- workspace boundaries;
- safe file operations;
- confirmation for destructive actions;
- secrets redaction;
- no silent software installation;
- no silent provider switching;
- no unrestricted autonomy;
- recoverable operations;
- append-only or auditable review history.

Convenience must not override file safety or traceability.

============================================================
16. PRODUCT SUCCESS METRICS
============================================================

Maintain local metrics that reflect actual product value.

Team behavior:

- direct-address routing accuracy;
- unnecessary responder rate;
- duplicate-response rate;
- successful handoff rate;
- unresolved loop count;
- context-consistency rate.

Trust:

- unsupported claim rate;
- evidence-backed completion rate;
- false-success rate;
- cancelled or interrupted runs incorrectly marked successful.

Quality:

- findings per task;
- repeated finding rate;
- rework cycles;
- qualification pass rate;
- standards compliance;
- artifact completeness.

Usability:

- time to first visible status;
- time to useful result;
- cancellation success;
- tasks completed without editing configuration files;
- management actions completed through GUI.

Learning:

- skills assigned;
- skills practiced;
- skills qualified;
- knowledge cards actually used;
- measurable quality change after training.

Do not optimize for message count or employee activity.

============================================================
17. DEFINITION OF DONE FOR MAJOR FEATURES
============================================================

A major feature is not complete because:

- a class exists;
- a database table exists;
- a UI tab exists;
- a test with mocks passes;
- an agent can describe the feature.

A major feature is ready only when:

1. It works through the interface.
2. It has explicit states.
3. It fails safely.
4. It is auditable.
5. It preserves existing behavior.
6. It has automated tests.
7. It has a user test plan.
8. It was tested in a real built application.
9. Limitations are documented.
10. It supports at least one permanent product goal.

Use statuses honestly:

- IMPLEMENTED_WITH_LIMITATIONS;
- READY_FOR_USER_TEST;
- REWORK_REQUIRED;
- BLOCKED.

Do not use COMPLETE before user validation.

============================================================
18. DEVELOPMENT PRIORITY RULE
============================================================

Before implementing a new feature, answer:

1. Does it improve real teamwork?
2. Does it improve measurable skill or knowledge quality?
3. Does it reduce the need for code/config editing?
4. Does it improve trust?
5. Does it improve daily usability?
6. Is there a simpler way to achieve the same result?
7. Does it create new uncontrolled autonomy?
8. Can the result be tested?

Features with weak answers should be deferred.

Do not expand the number of employees, roles or autonomous workflows faster than the system can manage them reliably.

============================================================
19. CURRENT DEVELOPMENT PRIORITIES
============================================================

Current priority order:

1. Realistic and disciplined team chat.
2. Reliable routing and conversation context.
3. Honest claims and evidence.
4. Understandable skill states and qualification.
5. Provider readiness and authentication.
6. Skill packages.
7. Knowledge and standards services.
8. Artifact and QA finding registries.
9. Training management.
10. Controlled multi-agent workflow.
11. Local-system stabilization.
12. Cloud-ready repository interfaces.
13. Server and web version.
14. Skill marketplace and paid specialization packages.

Do not skip foundational reliability in order to reach marketplace or cloud features early.

============================================================
20. LONG-TERM PRODUCT DIRECTION
============================================================

The local desktop application is the first implementation.

The future product may support:

- desktop client;
- web client;
- cloud server;
- user accounts;
- organizations;
- default employee teams;
- custom employee teams;
- team templates;
- server knowledge storage;
- synchronized projects;
- user-specific employee adaptation;
- paid skill packages;
- specialization packs;
- multiple providers;
- organization-level knowledge;
- marketplace content.

Prepare interfaces for this future, but do not prematurely replace the working local architecture.

Current local repositories should be abstractable later into:

- server API;
- relational database;
- object storage;
- authentication service;
- organization service;
- provider execution service.

============================================================
21. REQUIRED PRODUCT DOCUMENT
============================================================

Create:

docs/product/PRODUCT_NORTH_STAR.md

Store this complete product goal there.

Also create:

docs/product/PRODUCT_SUCCESS_METRICS.md
docs/product/DEFINITION_OF_DONE.md
docs/product/PRODUCT_ROADMAP.md

Update architecture and implementation reports to reference the North Star.

Every future phase report must include:

NORTH STAR IMPACT

- teamwork impact;
- skills/knowledge quality impact;
- no-code management impact;
- trust impact;
- user-experience impact.

If a phase does not improve any North Star criterion, explain why it was necessary.

============================================================
22. PERMANENT FINAL GOAL
============================================================

The desired result is:

A user opens Roman 2050 and works with a useful team of AI specialists.

The specialists understand the work, respect their roles, communicate naturally, use verified skills and knowledge, create real results, review each other, learn from evidence and remain under the user’s control.

The user does not maintain agent code.

The user manages a digital organization through a clear interface.

The system becomes more useful through work without becoming less trustworthy.

This is the permanent product goal.