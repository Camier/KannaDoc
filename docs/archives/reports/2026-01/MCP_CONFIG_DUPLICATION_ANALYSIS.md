# McpConfig.tsx Duplication Analysis

## Executive Summary

**File:** `/LAB/@thesis/layra/frontend/src/components/Workflow/NodeSettings/McpConfig.tsx` (534 lines)

**Finding:** McpConfig.tsx has **limited duplication** with other NodeSettings components. It uses a **different architectural pattern** (modal-based vs panel-based) that makes extraction to `NodeSettingsBase` **not valuable** (<100 lines potential savings).

**Recommendation:** **DO NOT EXTRACT** - Current structure is appropriate for this component's use case.

---

## 1. Architectural Pattern Comparison

### McpConfig.tsx - Modal Pattern
```typescript
// Standalone modal with own state management
<div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
  <div className="bg-white rounded-3xl px-10 py-6 min-w-[40%] max-w-[60%] max-h-[80vh] flex flex-col">
    {/* Content */}
  </div>
</div>
```

**Characteristics:**
- Self-contained modal overlay
- Direct `visible`/`setVisible` props
- Own form state management
- Vertical layout with scrolling
- Simpler lifecycle (open/edit/close)

### NodeSettingsBase Components - Panel Pattern
```typescript
// Panel in settings sidebar
<NodeSettingsBase node={node} translationNamespace="...">
  {(api) => (
    <>
      <NodeHeader ... />
      <DescriptionSection ... />
      <GlobalVariablesSection ... />
      <OutputSection ... />
    </>
  )}
</NodeSettingsBase>
```

**Characteristics:**
- Panel embedded in settings sidebar
- Complex state sharing (isDebugMode, codeFullScreenFlow)
- Composable sections via render props
- Advanced features (description editing, global variables, output debugging)
- Longer lifecycle (persistent during workflow editing)

---

## 2. Duplication Sources

### 2.1 Modal Wrapper Pattern (~40 lines)

**Found in:**
- McpConfig.tsx (lines 103-111)
- KnowledgeConfigModal.tsx (lines 188-189, 243-249)

**Pattern:**
```typescript
// Modal container
<div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
  <div className="bg-white rounded-3xl px-10 py-6 ...">
    {/* Header */}
    {/* Content with overflow */}
    {/* Action buttons */}
  </div>
</div>
```

**Potential Savings:** 20-30 lines if extracted to `ModalWrapper` component

**Caveat:** Modals have different internal structures, making extraction less valuable.

---

### 2.2 Add Item Input Pattern (~30 lines)

**Found in:**
- McpConfig.tsx (lines 124-177) - Add MCP config
- NodeSettingsBase.tsx (lines 345-389) - Add global variable
- FunctionNode.tsx (lines 369-425) - Add pip package

**Pattern:**
```typescript
<div className="flex items-center w-full px-2 gap-6 border-gray-200">
  <input
    value={itemName}
    placeholder={t("placeholder")}
    onChange={(e) => setItemName(e.target.value)}
    className="w-full px-4 py-1 border-2 border-gray-200 rounded-xl ..."
    onKeyDown={(e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addItem(itemName);
        setItemName("");
      }
    }}
  />
  <div onClick={() => addItem(itemName)} className="...">
    <svg>{plusIcon}</svg>
    <span>{t("addButton")}</span>
  </div>
</div>
```

**Potential Savings:** 15-20 lines per occurrence if extracted to `AddItemInput` component

**Caveat:** Each has unique validation and item creation logic.

---

### 2.3 Delete Confirmation Pattern (~25 lines)

**Found in:**
- McpConfig.tsx (lines 30-65, 513-521)
- KnowledgeConfigModal.tsx (lines 79-156, 262-268)
- FunctionNode.tsx (lines 82-192, 630-640)

**Pattern:**
```typescript
const [showConfirmDelete, setShowConfirmDelete] = useState<string | null>(null);

const confirmDelete = () => {
  if (showConfirmDelete) {
    deleteItem(showConfirmDelete);
    setShowConfirmDelete(null);
  }
};

const cancelDelete = () => {
  setShowConfirmDelete(null);
};

// In JSX
{showConfirmDelete && (
  <ConfirmDialog
    message={t("confirmDelete", { name: showConfirmDelete })}
    onConfirm={confirmDelete}
    onCancel={cancelDelete}
  />
)}
```

**Potential Savings:** 10-15 lines per occurrence if extracted to hook

**Caveat:** Already using shared `ConfirmDialog` component. Only state management differs.

---

### 2.4 Checkbox with Label Pattern (~20 lines)

**Found in:**
- McpConfig.tsx (lines 391-444, 450-491) - Toggle MCP tools
- FunctionNode.tsx (lines 296-333) - Toggle save image
- NodeSettingsBase.tsx (implicit in various sections)

**Pattern:**
```typescript
<label className="... inline-flex items-center ... cursor-pointer">
  <input
    type="checkbox"
    checked={isChecked}
    onChange={() => setChecked(!isChecked)}
    className="shrink-0 appearance-none h-4 w-4 border-1 border-gray-300 rounded-lg ..."
  />
  <svg className="absolute size-3 text-white shrink-0">
    {checkmarkIcon}
  </svg>
  <div className="ml-2 flex gap-1 items-center">
    <span>{t("label")}</span>
  </div>
</label>
```

**Potential Savings:** 10-15 lines per occurrence if extracted to `CheckboxLabel` component

**Caveat:** Most checkbox instances have unique layouts or handlers.

---

### 2.5 Details/Summary Accordion Pattern (~15 lines)

**Found in:**
- McpConfig.tsx (lines 189-221, 342-375)
- NodeSettingsBase.tsx (throughout sections)
- FunctionNode.tsx (lines 196-230, 495-554)

**Pattern:**
```typescript
<details className="group w-full space-y-2" open>
  <summary className="px-2 py-1 flex items-center cursor-pointer font-medium w-full gap-1">
    <svg>{icon}</svg>
    <div>{title}</div>
    <svg className="w-4 h-4 transition-transform group-open:rotate-180">
      {chevronDownIcon}
    </svg>
  </summary>
  <div className="px-2 flex flex-col ...">
    {/* Content */}
  </div>
</details>
```

**Potential Savings:** 5-10 lines per occurrence if extracted to `Accordion` component

**Caveat:** Native HTML `<details>` element is already simple. Extraction adds complexity.

---

## 3. Why NodeSettingsBase is Not Appropriate

### 3.1 Different Prop Interfaces

**NodeSettingsBase expects:**
```typescript
interface NodeSettingsBaseProps {
  node: CustomNode;
  isDebugMode: boolean;
  codeFullScreenFlow: boolean;
  setCodeFullScreenFlow: (value: boolean) => void;
  translationNamespace: string;
  children: (api: NodeSettingsAPI) => ReactNode;
}
```

**McpConfig uses:**
```typescript
interface McpConfigProps {
  node: CustomNode;
  visible: boolean;
  setVisible: Dispatch<SetStateAction<boolean>>;
}
```

**Mismatch:** McpConfig doesn't need `isDebugMode`, `codeFullScreenFlow`, or complex state management.

---

### 3.2 Different UI Structure

**NodeSettingsBase provides:**
- Editable description with Markdown preview
- Global variable management
- Output debugging section
- Panel-based layout

**McpConfig needs:**
- Modal overlay
- Simple list management
- Nested accordions for MCP configs
- No debugging or global variables

**Mismatch:** Using NodeSettingsBase would add unnecessary complexity.

---

### 3.3 Different Lifecycle

**NodeSettingsBase components:**
- Persist during workflow editing
- Support real-time output updates
- Handle debug mode toggling

**McpConfig:**
- Opens on demand
- Saves and closes immediately
- No persistent state during workflow editing

**Mismatch:** Different usage patterns make sharing inefficient.

---

## 4. Potential Extractions (with savings)

### 4.1 ModalWrapper Component (~20 lines)

```typescript
interface ModalWrapperProps {
  visible: boolean;
  onClose: () => void;
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  actions?: (onClose: () => void) => ReactNode;
}

export const ModalWrapper: React.FC<ModalWrapperProps> = ({
  visible,
  onClose,
  title,
  icon,
  children,
  actions,
}) => {
  if (!visible) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-3xl px-10 py-6 min-w-[40%] max-w-[60%] max-h-[80vh] flex flex-col">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {icon}
            <span className="text-lg font-medium">{title}</span>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
        {actions && (
          <div className="mt-4 pt-4 flex justify-end gap-2 border-t border-gray-200">
            {actions(onClose)}
          </div>
        )}
      </div>
    </div>
  );
};
```

**Usage in McpConfig:**
```typescript
<ModalWrapper
  visible={visible}
  onClose={onClose}
  title={t("title")}
  icon={<McpIcon />}
  actions={(onClose) => (
    <>
      <button onClick={onClose}>{t("cancelButton")}</button>
      <button onClick={handleSubmit}>{t("saveButton")}</button>
    </>
  )}
>
  {/* MCP config content */}
</ModalWrapper>
```

**Savings:** ~20 lines per modal (3 modals = 60 lines total)

---

### 4.2 AddItemInput Component (~15 lines)

```typescript
interface AddItemInputProps {
  value: string;
  onChange: (value: string) => void;
  onAdd: () => void;
  placeholder: string;
  addButtonLabel: string;
  disabled?: boolean;
}

export const AddItemInput: React.FC<AddItemInputProps> = ({
  value,
  onChange,
  onAdd,
  placeholder,
  addButtonLabel,
  disabled = false,
}) => {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      onAdd();
    }
  };

  return (
    <div className="flex items-center w-full px-2 gap-6 border-gray-200">
      <input
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        className="w-full px-4 py-1 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
        disabled={disabled}
      />
      <div
        onClick={onAdd}
        className={`whitespace-nowrap pr-2 flex items-center gap-1 text-indigo-500 ${
          !disabled ? "cursor-pointer hover:text-indigo-700" : "cursor-not-allowed opacity-50"
        }`}
      >
        <PlusIcon />
        <span>{addButtonLabel}</span>
      </div>
    </div>
  );
};
```

**Usage in McpConfig:**
```typescript
<AddItemInput
  value={mcpName}
  onChange={setMcpName}
  onAdd={() => {
    if (mcpName) {
      addMcpConfig(node.id, mcpName, { mcpServerUrl: "", mcpTools: [] });
      setMcpName("");
    }
  }}
  placeholder={t("mcpNamePlaceholder")}
  addButtonLabel={t("addButton")}
/>
```

**Savings:** ~15 lines × 5 occurrences = 75 lines total

---

### 4.3 CheckboxLabel Component (~10 lines)

```typescript
interface CheckboxLabelProps {
  checked: boolean;
  onChange: () => void;
  label: string;
  disabled?: boolean;
  className?: string;
}

export const CheckboxLabel: React.FC<CheckboxLabelProps> = ({
  checked,
  onChange,
  label,
  disabled = false,
  className = "",
}) => {
  return (
    <label
      className={`text-sm w-full overflow-auto inline-flex items-center group px-2 rounded-xl hover:bg-gray-50 ${
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"
      } ${className}`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className="shrink-0 appearance-none h-4 w-4 border-1 border-gray-300 rounded-lg transition-colors checked:bg-indigo-500 checked:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-200"
      />
      <CheckmarkIcon />
      <div className="ml-2 flex gap-1 items-center">
        <span>{label}</span>
      </div>
    </label>
  );
};
```

**Savings:** ~10 lines × 8 occurrences = 80 lines total

---

## 5. Total Potential Savings

| Component | Lines Saved | Occurrences | Total Savings |
|-----------|-------------|-------------|---------------|
| ModalWrapper | 20 | 3 | 60 |
| AddItemInput | 15 | 5 | 75 |
| CheckboxLabel | 10 | 8 | 80 |
| **Grand Total** | - | - | **215 lines** |

**Breakdown by file:**
- McpConfig.tsx: ~70 lines (13% reduction)
- KnowledgeConfigModal.tsx: ~60 lines (15% reduction)
- FunctionNode.tsx: ~50 lines (8% reduction)
- NodeSettingsBase.tsx: ~35 lines (6% reduction)

---

## 6. Cost-Benefit Analysis

### Benefits of Extraction
- **215 lines** of code reduction across NodeSettings components
- Consistent UI patterns (modal wrapper, inputs, checkboxes)
- Easier maintenance (single source of truth for common patterns)
- Improved accessibility (consistent ARIA labels in shared components)

### Costs of Extraction
- **3 new component files** to maintain
- **Additional prop interfaces** to document
- **Potential over-abstraction** (each usage has unique requirements)
- **Refactoring risk** (introducing bugs during extraction)
- **Reduced readability** (more indirection, harder to follow logic flow)

### Net Assessment
**Marginal benefit for McpConfig specifically** (~70 lines saved = 13% reduction)

**Better value** if extracted for **entire NodeSettings ecosystem** (~215 lines total)

---

## 7. Recommendation

### For McpConfig.tsx Specifically
**DO NOT extract to NodeSettingsBase** - reasons:
1. Different architectural pattern (modal vs panel)
2. Simpler state management needs
3. Would require adding unnecessary props (`isDebugMode`, `codeFullScreenFlow`)
4. Current structure is clear and appropriate for use case

### For NodeSettings Ecosystem Overall
**CONSIDER extracting shared components** - reasons:
1. 215 lines total savings across all components
2. Patterns are truly duplicated (modal wrapper, add item input, checkbox label)
3. Components have simple, stable interfaces
4. Would improve consistency and maintainability

### Proposed Priority Order
1. **High Priority:** Extract `AddItemInput` (75 lines savings, 5 occurrences)
2. **Medium Priority:** Extract `CheckboxLabel` (80 lines savings, but more unique cases)
3. **Low Priority:** Extract `ModalWrapper` (60 lines savings, but modals vary significantly)

---

## 8. Conclusion

**McpConfig.tsx analysis:** Component has limited duplication with others. Uses modal pattern instead of NodeSettingsBase panel pattern. Current structure is appropriate.

**Extraction value:** Low for McpConfig alone (~70 lines), moderate for ecosystem (~215 lines).

**Recommendation:** Do not extract McpConfig to NodeSettingsBase. Consider shared component extraction for entire NodeSettings ecosystem if code duplication becomes maintenance burden.

**Current state is acceptable** - duplication is minimal and patterns are context-appropriate.

---

## Appendix: File Statistics

| File | Lines | Pattern | Potential Savings |
|------|-------|---------|-------------------|
| McpConfig.tsx | 534 | Modal | ~70 lines |
| KnowledgeConfigModal.tsx | 397 | Modal | ~60 lines |
| FunctionNode.tsx | 647 | NodeSettingsBase | ~50 lines |
| NodeSettingsBase.tsx | 616 | Base Component | ~35 lines |
| **Total** | **2194** | - | **~215 lines (10%)** |

**Note:** McpConfig.tsx is 534 lines. After potential extractions, it would be ~464 lines (13% reduction).
