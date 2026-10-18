# Tutor IQ · OS-DBX (sky blue)

Your OS-DBX Process lab (FCFS, SJF, Priority, Round Robin) in the Tutor IQ design.

## Run
```bash
npm install
npm run dev      # http://localhost:5173
npm run build
```

## Customize
- Text, dashboard preview, labs, FAQ: `src/content.ts`
- Colors, fonts, radii, shadows: `tailwind.config.ts`
- Scheduling logic: `src/lib/scheduler.ts`
- Blimp artwork: `src/components/Blimp.tsx`; clouds and sun: `src/components/Sky.tsx`
- Headline highlight word: `hero.mark` in `content.ts`
