# Frontend Theming Guide

This document covers the theming system used in the LAYRA frontend, including dark mode setup, color patterns, and the rebuild process.

## 1. Dark Mode Setup

LAYRA uses Tailwind CSS for styling and handles dark mode using the `class` strategy.

- **Tailwind Config**: The `darkMode` option is set to `class` in `tailwind.config.ts`.
- **HTML Class**: The `className="dark"` is applied to the `<html>` tag in `layout.tsx` to enable dark mode globally or conditionally.
- **Body Background**: The default background for the dark theme is typically `bg-gray-900`.

## 2. Color Patterns Reference

When building components, use the following standard color patterns to ensure consistency across light and dark modes.

### Text Colors
| Usage | Light Mode | Dark Mode | Class Example |
|-------|------------|-----------|---------------|
| Primary Text | `gray-900` | `gray-100` | `text-gray-900 dark:text-gray-100` |
| Secondary Text | `gray-700` | `gray-200` | `text-gray-700 dark:text-gray-200` |
| Muted Text | `gray-500` | `gray-400` | `text-gray-500 dark:text-gray-400` |
| Max Contrast | `black` | `white` | `text-black dark:text-white` |

### Backgrounds
| Surface | Light Mode | Dark Mode | Class Example |
|---------|------------|-----------|---------------|
| Main | `white` | `gray-900` | `bg-white dark:bg-gray-900` |
| Secondary | `gray-50` | `gray-800` | `bg-gray-50 dark:bg-gray-800` |
| Tertiary | `gray-100` | `gray-800` | `bg-gray-100 dark:bg-gray-800` |

### Borders
| Usage | Light Mode | Dark Mode | Class Example |
|-------|------------|-----------|---------------|
| Default | `gray-200` | `gray-700` | `border-gray-200 dark:border-gray-700` |
| Strong | `gray-300` | `gray-600` | `border-gray-300 dark:border-gray-600` |

### Hover States
| Usage | Light Mode | Dark Mode | Class Example |
|-------|------------|-----------|---------------|
| Light Hover | `gray-100` | `gray-700` | `hover:bg-gray-100 dark:hover:bg-gray-700` |
| Subtle Hover | `gray-50` | `gray-800` | `hover:bg-gray-50 dark:hover:bg-gray-800` |

### Accent Colors
Accents often use the same base color but may have slight adjustments for dark mode if needed.
```tsx
// Buttons / Primary Actions
bg-indigo-500 hover:bg-indigo-600

// Links / Text Accents
text-indigo-500 dark:text-indigo-400
```

## 3. Frontend Rebuild Process

After making changes to the frontend code or styling, follow these steps to rebuild the environment.

```bash
# After making frontend changes:
cd /LAB/@thesis/layra

# Option 1: Quick rebuild (uses cache)
./scripts/compose-clean up -d --build frontend

# Option 2: Full rebuild (no cache - use if changes don't appear)
./scripts/compose-clean build --no-cache frontend
./scripts/compose-clean up -d frontend

# Always restart nginx after frontend rebuild
./scripts/compose-clean restart nginx

# Hard refresh browser: Ctrl+Shift+R
```

## 4. Key Files

- `frontend/tailwind.config.ts`: Configuration for dark mode, themes, and plugins.
- `frontend/src/app/[locale]/layout.tsx`: Root layout where the `dark` class is managed.
- `frontend/src/app/globals.css`: Global CSS variables and Tailwind directives.

## 5. Troubleshooting

- **Changes not appearing?**: Docker might be using stale layers. Run the build with the `--no-cache` flag.
- **Dark mode not working?**: Verify that `darkMode: "class"` is present in `tailwind.config.ts` and that the `dark` class is actually on the `<html>` element.
- **Text invisible?**: This often happens if a text color is defined for light mode but lacks a `dark:` variant (e.g., `text-gray-900` on a dark background). Always add a `dark:` variant.

## 6. Adding New Components

When creating new UI components, always ensure they are theme-aware. Include `dark:` variants for:
- All text colors
- All background colors
- All border colors
- All hover and active states
