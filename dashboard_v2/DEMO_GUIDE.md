# ORCA dashboard: demo and presenter guide

## Start here

From the repository root, run:

```bash
.venv/bin/python dashboard_v2/run.py --server.port 8503
```

Open http://127.0.0.1:8503 and choose **Start guided demo** in the sidebar.
No API key or internet connection is needed for this walkthrough after dependencies are installed.
The walkthrough runs the school-bus scenario with seed 7 using **scripted agents**.
These are deterministic stand-ins, not live language-model answers. Their labels remain visible.
Your current live simulation is kept separately; **Exit demo** returns to it.

The five checkpoints stay paused until you press **Next step**. You can go back, restart,
or explore another workspace and return to the current step. Checkpoints come from actual
simulation events, rather than arbitrary timers. Presenter notes are available in the dashboard.
Larger presentation text turns on automatically for the demo. Exiting the demo restores
the regular text size.

## A five-minute presentation

1. **Meet the town — 40 seconds.**
   Show the map, available ambulances, and hospital cards.
   Say: “The problem is coordinating limited ambulances and hospital capacity when a large
   emergency arrives. The closest hospital may not have the capability or space a patient needs.”
2. **Receive the emergency — 50 seconds.**
   Show the selected call in the incident desk, triage categories, and the call-to-care timeline.
   Say: “The simulation records calls, proposed assignments, safety validation, and patient
   milestones. We can trace the response from the first call.”
3. **Follow the negotiation — 70 seconds.**
   Read an actual proposal and hospital reply in Decision room. Point to the source label.
   Say: “The assessor, dispatcher, hospital agents, and allocator have different responsibilities.
   This offline walkthrough demonstrates that workflow with scripted stand-ins. The engine
   validates actions before committing them.”
4. **See patients reach care — 50 seconds.**
   Compare hospital capabilities, free beds, and incoming patients in Hospital network.
   Say: “The first patient has started treatment. Routing must consider capacity and capability,
   while hospital load continues changing.” Bed bars show **occupied** capacity; numbers show
   **free / total**. A private hospital can have additional contract restrictions.
5. **Explain the outcomes — 60 seconds.**
   Show Run report. Read treatment times, patients who reached care, and deaths together.
   Say: “These are outcomes for one synthetic run. This screen alone does not show that agents
   beat a baseline. That claim requires controlled comparisons using identical scenarios.”

Allow 30 seconds for questions. For a shorter demo, combine the first two steps and read one
proposal/reply. For a longer demo, open Ambulance fleet, inspect another incident, and explain
how recorded logs can be replayed. Avoid changing live scenario settings mid-presentation.

## Where to find everything

| Workspace | Find here |
| --- | --- |
| Response overview | Map, searchable incident picker, response milestones, hospital summary, recent actions |
| Hospital network | Bed availability, capabilities, incoming patients, and patient distribution |
| Ambulance fleet | Every unit, assignment, destination, time in status, and private standby resources |
| Decision room | Proposals, replies, source labels, filters, and detailed call records |
| Run report | Dispatch/scene/care timings, outcomes, saved scorecards, and event-log download |
| Help | Workspace directory, definitions, and a downloadable copy of this guide |

An incident selection is retained while moving between workspaces. Search the incident picker
by emergency name or ID, or click its map marker. Use **All incidents** to remove the focus.
Triage labels: red = critical, yellow = serious, green = minor, black = expectant in the simulator.
“Reached care” includes patients who have already been discharged. Map locations are assignment
positions in a fictional town, not live GPS tracks.

## Research behind the usability changes

The following are design principles applied to this product, not findings from testing ORCA
with users. A short rehearsal with someone unfamiliar with the project is still useful.

- **Make state visible:** clear run mode, source labels, paused demo checkpoints, and current
  simulation time apply NN/g's [Visibility of System Status](https://www.nngroup.com/articles/visibility-system-status/).
- **Prefer recognizable choices:** emergency names accompany incident IDs, a workspace directory
  explains where features live, and a dedicated fleet page avoids requiring users to remember
  a hidden section. See [Recognition and Recall](https://www.nngroup.com/articles/recognition-and-recall/).
- **Reveal detail when needed:** raw agent records, advanced settings, and presenter notes are
  secondary to the main task. See [Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/).
- **Organize around tasks:** independent workspaces support exploration, while a separate guided
  sequence supports presenting. This adapts [GOV.UK's navigation guidance](https://design-system.service.gov.uk/patterns/navigate-a-service/)
  to the two different workflows; it is not a claim of GOV.UK compliance.
- **Explain colored indicators:** status words, triage labels, and numerical bed counts accompany
  the colored markers. This follows the principle in W3C's [Use of Color guidance](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)
  that color needs an additional visible cue. No accessibility conformance audit is claimed.
