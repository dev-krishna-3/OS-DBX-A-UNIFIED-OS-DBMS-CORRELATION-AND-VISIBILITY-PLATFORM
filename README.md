# OS-DBX Student Frontend

A no-build, dependency-free browser frontend for the OS-DBX educational platform. The first screen is an interactive CPU scheduling lab (FCFS, SJF, non-preemptive Priority, Round Robin) written so a 13–14 year old can follow it.

## Run it

Open `index.html` in a modern browser. No install and no backend needed; the simulation runs locally in the page.

## Structure

- `index.html` — two views in one page: **Home** (status strip, nine-lab grid, how it connects) and the **Process lab** (hero, 3-step lab, results stage, glossary), plus a help dialog
- `styles.css` — same warm paper / olive / lime / coral theme as before, organised in numbered sections with all keyframes in one place
- `app.js` — process editor, schedulers (each block also records *why* it was chosen), playback, summary and comparison

## Navigation

The sidebar and the home grid follow the nine-view plan: 01 Process lab, 02 Query watcher, 03 Transactions, 04 Connect the dots, 05 Deadlock graph, 06 Incident replay, 07 Conflict checker, 08 Recovery sandbox, 09 Impact & speed. Only 01 is built; the others show a "coming soon" note. Each has a kid-friendly name, and the technical name can sit in its own page later.

The backend dot on Home pings `http://127.0.0.1:8000/health`. If it is off, the page says so and the lab keeps working. The event-stream numbers stay as dashes until real data is wired in.

## Learning design

- **One idea throughout:** the CPU is a cashier, processes are customers. The help dialog, the glossary and the stage all use it.
- **Plain-English narration:** every step explains why the CPU picked that process.
- **Stage view:** Not here yet → Waiting line → On the CPU → Finished, so students see the queue move, not just a chart.
- **Compare:** after a run, the other three rules are scored on the same processes and can be tried with one tap.
- **Sidebar challenge:** run all four rules to complete it.

## Animations (one per feature)

| Feature | Motion |
| --- | --- |
| Hero | Queue of processes walking up to the CPU |
| Rule cards | FCFS bars line up, SJF short bar jumps ahead, Priority star pops, Round robin arrow spins |
| Time quantum | Opens smoothly only for Round robin |
| + / − steppers | Number bumps; wrong input shakes |
| Process rows | Highlight in when added, fade out when removed |
| Stage | Chips slide into the line, pop onto the CPU, bounce into Finished; CPU glows while running |
| Timeline | Blocks grow from the left; a marker follows the current block |
| Results | Numbers count up; wait bars grow one after another |
| Challenge | Tick pops with a small burst |
| Help dialog | Springs in, rows appear one by one |

All motion respects `prefers-reduced-motion`.

## Scope

This is the frontend foundation, not the complete nine-view product. Deadlock, memory and process states appear as "coming soon". Backend API integration can be added as those endpoints are ready.
