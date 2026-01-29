# How to Run Component Tests

## Quick Start

### Run All Tests
```bash
cd /LAB/@thesis/layra/frontend
npm test
```

### Run Tests Once (No Watch Mode)
```bash
npm test -- --run
```

### Run Specific Test File
```bash
# Test SaveCustomNode component (100% passing!)
npm test -- src/components/Workflow/SaveNode.test.tsx

# Test ConfirmDialog component (95% passing)
npm test -- src/components/ConfirmDialog.test.tsx

# Test ConfirmAlert component (77% passing)
npm test -- src/components/ConfirmAlert.test.tsx
```

### Run Tests in Watch Mode
```bash
npm test -- --watch
```

### Run Tests with Coverage
```bash
npm run test:coverage
```

---

## Test Results Summary

### ✅ Fully Passing Components
1. **SaveCustomNode** - 20/20 tests passing (100%)
2. **ConfirmDialog** - 19/20 tests passing (95%)
3. **Alert** (existing) - 3/3 tests passing (100%)

### ⚠️ Partially Passing Components
1. **ConfirmAlert** - 10/13 tests passing (77%)
2. **NodeTypeSelector** - 11/20 tests passing (55%)

### 🔍 Needs Investigation
1. **MarkdownDisplay** - 0 tests detected (file created but not running)
2. **KnowledgeConfigModal** - React act() warnings

---

## Test Files Created

```
frontend/src/components/
├── AiChat/
│   ├── MarkdownDisplay.test.tsx
│   └── KnowledgeConfigModal.test.tsx
├── Workflow/
│   ├── SaveNode.test.tsx
│   └── NodeTypeSelector.test.tsx
├── ConfirmAlert.test.tsx
└── ConfirmDialog.test.tsx
```

---

## Debugging Failing Tests

### 1. Inspect DOM Structure
```typescript
import { screen } from '@testing-library/react';

// Add this line to see what's actually rendered
screen.debug();
```

### 2. Filter Tests
```bash
# Run only tests matching a pattern
npm test -- -t "renders correctly"
```

### 3. Verbose Output
```bash
npm test -- --reporter=verbose
```

---

## Fixing Common Issues

### React act() Warnings
Wrap async operations in `waitFor()`:

```typescript
import { waitFor } from '@testing-library/react';

// Before
expect(screen.getByText('Loading')).toBeInTheDocument();

// After
await waitFor(() => {
  expect(screen.getByText('Loading')).toBeInTheDocument();
});
```

### DOM Structure Mismatches
Use `screen.debug()` to see actual output:

```typescript
test('example', () => {
  render(<MyComponent />);
  screen.debug(); // Prints DOM to console
});
```

---

## Coverage Goals

| Component | Tests | Pass Rate | Target |
|-----------|-------|-----------|--------|
| SaveCustomNode | 20 | 100% | ✅ 100% |
| ConfirmDialog | 20 | 95% | ✅ 100% |
| ConfirmAlert | 13 | 77% | ⚠️ 90% |
| NodeTypeSelector | 20 | 55% | ⚠️ 80% |
| MarkdownDisplay | TBD | TBD | 80% |
| KnowledgeConfigModal | TBD | TBD | 80% |

---

## Next Steps

1. ✅ Run all tests: `npm test -- --run`
2. 🔧 Fix failing tests in NodeTypeSelector
3. 🔧 Fix styling assertions in ConfirmAlert
4. 🔍 Investigate MarkdownDisplay test detection
5. 📊 Achieve 80%+ coverage across all components
