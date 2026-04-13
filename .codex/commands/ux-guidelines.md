Apply these UX 10/10 principles to ALL frontend work on the Scouter dashboard.

## Core Principles

1. **No redundant information** — never show the same data in two places on the same page. If health status is in the strip, it doesn't go in the control center too.

2. **Progressive disclosure** — show the essential first, details on demand. Use collapsible sections, expandable rows, and "ver mas" toggles. Don't overwhelm with 11 cards when 4 tell the story.

3. **No layout shift** — NEVER replace content with a loading spinner on background refreshes. Only show loading states on initial load. Use `useRef(true)` for `isInitialLoad` pattern:
   ```typescript
   const isInitial = useRef(true);
   const load = useCallback(async () => {
     if (isInitial.current) setLoading(true);
     try { ... } finally {
       setLoading(false);
       isInitial.current = false;
     }
   }, []);
   ```

4. **Minimal API calls** — consolidate data fetching. Share hooks across components (`useSystemHealth`). Don't fetch 200 objects when you need 8. Don't call the same endpoint from two components.

5. **Clear visual hierarchy** — top to bottom should follow importance: status > controls > metrics > trends > details. The most actionable info goes first.

6. **Think like the user** — a developer checking this dashboard wants to know: Is the system healthy? What are my numbers? Are there trends? What happened recently? Design for that flow.

7. **Skeleton loaders, not spinners** — loading states should maintain the same layout dimensions. Use `SkeletonStatCard`, `SkeletonCard`, or matching placeholder shapes.

8. **Spanish (es-AR) everywhere** — all labels, hints, empty states, error messages, button text. No switching between languages on the same screen.

9. **Consistent error states** — every component that fetches data should have a recoverable error state. Don't fail silently. Show what went wrong and offer a retry action.

10. **Collapsible sections default wisely** — primary content opens by default, secondary content starts collapsed. Persist collapse state if the section is frequently toggled.

## Anti-Patterns to Avoid

- Fetching the same endpoint from multiple components on the same page
- Showing "Chequeando..." or "Cargando..." on every background poll
- Displaying identical metrics in different sections with slightly different labels
- Using `setLoading(true)` on every call including background refreshes
- Making API calls for data that could be derived from data you already have
- Adding a new section when the data belongs in an existing one
