# Domain Packages

Domain packages contain specialized data and policies:

- PCB/KiCad: standards, schematic/layout skills, ERC/DRC tools and review rules.
- Software: language/tool skills, source artifacts, tests and release checks.
- Culinary: recipe skills, source verification, food safety and review rules.

Packages depend on the generic platform. The generic platform does not import
PCB, software or culinary concepts. Adding a new domain should require data,
skills, tools, standards and templates, not edits to organization routing.
