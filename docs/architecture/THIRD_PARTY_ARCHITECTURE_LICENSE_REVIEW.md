# Third-Party Architecture and License Review

Review date: 2026-08-13. This is an engineering review, not legal advice. Before
commercial redistribution, legal counsel must verify the exact shipped versions
and all transitive dependency notices.

| Project | Inspected license | Commercial use / modification | Redistribution obligations | Risk and decision |
|---|---|---|---|---|
| Microsoft Agent Framework | MIT, commit `6d25fb1` | Permitted | Preserve copyright and license text | Low license risk; high dependency/API-maturity risk |
| LangGraph | MIT, commit `644815f` | Permitted | Preserve copyright and license text | Low; preferred optional adapter candidate |
| OpenHands Software Agent SDK | MIT, commit `ceda00b` | Permitted | Preserve copyright and license text | Low core license risk; audit 128 resolved packages and optional services |
| AG2 | Apache-2.0, commit `088f280` | Permitted, explicit patent grant | Preserve license/NOTICE; mark modified files where required | Low-to-medium compliance workload |
| Langfuse | MIT outside listed enterprise directories; `e415269` | Core/SDK permitted; enterprise paths governed separately | Preserve MIT notice; do not assume `/ee` rights | Medium if self-host server code is bundled; low for SDK-only backend |
| Temporal Python SDK | MIT, commit `73bdb36` | Permitted | Preserve notice | SDK low risk; server/service licensing and operations are separate decisions |

Primary license sources are the LICENSE files in the official
[MAF](https://github.com/microsoft/agent-framework),
[LangGraph](https://github.com/langchain-ai/langgraph),
[OpenHands SDK](https://github.com/OpenHands/software-agent-sdk),
[AG2](https://github.com/ag2ai/ag2),
[Langfuse](https://github.com/langfuse/langfuse), and
[Temporal SDK](https://github.com/temporalio/sdk-python) repositories.

## Commercial safeguards

1. Pin every adopted dependency and produce an SBOM/notices bundle at release.
2. Scan transitive licenses; the framework license does not cover all packages.
3. Keep optional telemetry opt-in and document what leaves the local machine.
4. Do not copy examples or server enterprise directories into Team2050 without
   a source-specific review.
5. Keep framework APIs behind Team2050 interfaces so a legal or commercial
   change does not force changes in product entities.
