# Frontend UX Patterns

Quick reference for consistent, accessible patterns in the Fikiri frontend.

## Tooltips and hover-revealed content

When adding help text or descriptions that appear on hover:

1. **Trigger on the control only**  
   Attach `onMouseEnter` / `onMouseLeave` to the **help icon** (e.g. `HelpCircle`), not to the whole card or a large container. Otherwise the tooltip appears when hovering anywhere and can overlap the card.

2. **Position to avoid overlap**  
   - Prefer **above** the trigger: `bottom-full`, `left-1/2 -translate-x-1/2`, `mb-2` or `mb-3`.  
   - Use a high `z-index` (e.g. `z-[100]`) so the tooltip stays above surrounding content.  
   - Add `pointer-events-none` on the tooltip so it doesn’t capture the cursor.  
   - Ensure the parent that contains the trigger has `overflow-visible` if the tooltip would be clipped.

3. **Reference implementation**  
   See `frontend/src/components/EnhancedMetricCard.tsx`: tooltip is shown only when hovering the `HelpCircle` icon, positioned above and centered, with `stopPropagation()` on the icon wrapper so card hover doesn’t trigger it.

## Modals and scroll

- Modal overlays: use `overflow-y-auto` on the overlay so the page can scroll when the modal is tall or when the viewport is small.  
- Modal content: use flex layout with `flex-shrink-0` on header/footer and `flex-1 min-h-0` on the scrollable body.  
- See: `AccountManagement.tsx`, `OnboardingWizard.tsx`, `CustomizationPanel.tsx`.

## Long pages and fixed height

- For list/detail layouts (e.g. inbox), give the scrollable content area a max height (e.g. `max-h-[calc(100vh-250px)]`) and `overflow-y-auto` so the page doesn’t grow without bound.  
- Prefer constraining scroll to the content area instead of the whole page when the layout has a persistent header/sidebar.
