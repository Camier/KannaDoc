# McpConfig.tsx Code Duplication Analysis - Summary

## Quick Facts

**File:** `/LAB/@thesis/layra/frontend/src/components/Workflow/NodeSettings/McpConfig.tsx`
**Lines:** 534
**Analysis Date:** 2026-01-27

---

## Bottom Line

**McpConfig.tsx does NOT have significant code duplication** that warrants extraction to `NodeSettingsBase`. The component uses a **modal-based architecture** while `NodeSettingsBase` provides a **panel-based architecture**. These are fundamentally different patterns with different use cases.

**Recommendation:** **Keep current structure** - it's appropriate for this component's needs.

---

## Key Findings

### 1. Architectural Mismatch

| Aspect | McpConfig | NodeSettingsBase |
|--------|-----------|------------------|
| **Pattern** | Modal overlay | Settings panel |
| **Visibility** | `visible` boolean prop | Always visible in sidebar |
| **Lifecycle** | Open → Edit → Close | Persistent during workflow editing |
| **State** | Simple form state | Complex (debug mode, fullscreen code, etc.) |
| **Layout** | Vertical with scrolling | Composable sections |
| **Features** | List management | Description editing, global vars, output debugging |

### 2. Duplication Sources

McpConfig shares patterns with **2 other modal components**:

1. **McpConfig.tsx** (534 lines) - MCP server configuration
2. **KnowledgeConfigModal.tsx** (397 lines) - Knowledge base + model configuration
3. **McpAdvancedSettings.tsx** (260 lines) - Advanced MCP settings

**Total ecosystem:** 1,191 lines across 3 modal components

### 3. Potential Extraction Value

**If extracting shared components for ALL 3 modals:**

| Component | Savings | Occurrences | Value |
|-----------|---------|-------------|-------|
| `ModalWrapper` | 20 lines × 3 = 60 lines | 3 | **Medium** |
| `AddItemInput` | 15 lines × 5 = 75 lines | 5 (across all NodeSettings) | **High** |
| `CheckboxLabel` | 10 lines × 8 = 80 lines | 8 (across all NodeSettings) | **Medium** |
| **Total** | **215 lines** | - | **10% of NodeSettings code** |

**For McpConfig specifically:** ~70 lines savings (13% reduction)

---

## Why NodeSettingsBase Doesn't Fit

### 1. Wrong Props Interface

```typescript
// NodeSettingsBase expects (7 props)
interface NodeSettingsBaseProps {
  node: CustomNode;
  isDebugMode: boolean;              // ❌ McpConfig doesn't need
  codeFullScreenFlow: boolean;       // ❌ McpConfig doesn't need
  setCodeFullScreenFlow: ...;        // ❌ McpConfig doesn't need
  translationNamespace: string;
  children: (api: NodeSettingsAPI) => ReactNode;
}

// McpConfig has (3 props)
interface McpConfigProps {
  node: CustomNode;
  visible: boolean;                  // ✅ McpConfig needs
  setVisible: Dispatch<...>;         // ✅ McpConfig needs
}
```

### 2. Wrong Features

**NodeSettingsBase provides:**
- Editable description with Markdown preview
- Global variable management
- Output debugging section
- Panel-based composable sections

**McpConfig needs:**
- Modal overlay
- Simple list management
- Nested accordions
- No debugging or global variables

### 3. Different Usage Pattern

```typescript
// NodeSettingsBase - Persistent panel during workflow editing
<Panel>
  <NodeSettingsBase>
    {(api) => <DescriptionSection api={api} />}
    {(api) => <GlobalVariablesSection api={api} />}
    {(api) => <OutputSection api={api} />}
  </NodeSettingsBase>
</Panel>

// McpConfig - On-demand modal
<Button onClick={() => setVisible(true)}>Configure MCP</Button>
{visible && (
  <McpConfigModal
    visible={visible}
    setVisible={setVisible}
    onSave={handleSave}
  />
)}
```

---

## Shared Patterns Across ALL NodeSettings

While McpConfig shouldn't use NodeSettingsBase, there ARE patterns duplicated across the entire NodeSettings ecosystem:

### 1. Modal Wrapper (3 occurrences)

```typescript
// Used in: McpConfig, KnowledgeConfigModal, McpAdvancedSettings
<div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
  <div className="bg-white rounded-3xl px-10 py-6 min-w-[40%] max-w-[60%] max-h-[80vh] flex flex-col">
    {/* Header */}
    {/* Content */}
    {/* Actions */}
  </div>
</div>
```

**Extract to:** `ModalWrapper` component
**Savings:** 60 lines total

### 2. Add Item Input (5 occurrences)

```typescript
// Used in: McpConfig, NodeSettingsBase, FunctionNode, KnowledgeConfigModal
<div className="flex items-center w-full px-2 gap-6 border-gray-200">
  <input
    value={item}
    onChange={(e) => setItem(e.target.value)}
    onKeyDown={(e) => e.key === "Enter" && addItem()}
    className="w-full px-4 py-1 border-2 border-gray-200 rounded-xl ..."
  />
  <button onClick={addItem} className="...">
    <PlusIcon />
    <span>{t("add")}</span>
  </button>
</div>
```

**Extract to:** `AddItemInput` component
**Savings:** 75 lines total

### 3. Checkbox with Label (8 occurrences)

```typescript
// Used in: McpConfig (×4), FunctionNode, NodeSettingsBase, etc.
<label className="inline-flex items-center group px-2 rounded-xl hover:bg-gray-50 cursor-pointer">
  <input
    type="checkbox"
    checked={checked}
    onChange={onChange}
    className="appearance-none h-4 w-4 border-1 border-gray-300 rounded-lg checked:bg-indigo-500 ..."
  />
  <CheckmarkIcon />
  <div className="ml-2"><span>{label}</span></div>
</label>
```

**Extract to:** `CheckboxLabel` component
**Savings:** 80 lines total

---

## Recommendation Matrix

### For McpConfig.tsx Specifically

| Approach | Savings | Complexity | Recommendation |
|----------|---------|------------|----------------|
| **Use NodeSettingsBase** | 0 lines | High | ❌ **Not appropriate** - wrong architectural pattern |
| **Extract shared modal components** | ~70 lines | Medium | 💡 **Consider** - if other modals also extracted |
| **Keep as-is** | 0 lines | Low | ✅ **Recommended** - current structure is appropriate |

### For NodeSettings Ecosystem

| Component | Savings | Occurrences | Effort | Value |
|-----------|---------|-------------|--------|-------|
| `AddItemInput` | 75 lines | 5 | Low | ⭐⭐⭐ **High** |
| `CheckboxLabel` | 80 lines | 8 | Low | ⭐⭐ **Medium** - many unique cases |
| `ModalWrapper` | 60 lines | 3 | Medium | ⭐⭐ **Medium** - modals vary significantly |
| **Total** | **215 lines** | - | - | **10% reduction** |

---

## Conclusion

### McpConfig.tsx Assessment
- **Current structure is appropriate** for its use case
- **Not a candidate for NodeSettingsBase** due to architectural differences
- **Has minor duplication** with other modal components (~70 lines)
- **Recommendation:** Keep as-is, unless undertaking broader NodeSettings refactoring

### If Refactoring Entire NodeSettings Ecosystem
- **Extract `AddItemInput`** first (highest value, lowest complexity)
- **Consider `CheckboxLabel`** second (many occurrences but unique cases)
- **Defer `ModalWrapper`** until modals stabilize (currently vary significantly)

### Documentation
Full analysis: `/LAB/@thesis/layra/docs/MCP_CONFIG_DUPLICATION_ANALYSIS.md`
This summary: `/LAB/@thesis/layra/docs/MCP_CONFIG_ANALYSIS_SUMMARY.md`

---

## Quick Reference: File Locations

**McpConfig.tsx:**
```
/LAB/@thesis/layra/frontend/src/components/Workflow/NodeSettings/McpConfig.tsx
```

**Related modal components:**
```
/LAB/@thesis/layra/frontend/src/components/Workflow/NodeSettings/KnowledgeConfigModal.tsx
/LAB/@thesis/layra/frontend/src/components/Workflow/NodeSettings/McpAdvancedSettings.tsx
```

**NodeSettingsBase (for comparison):**
```
/LAB/@thesis/layra/frontend/src/components/Workflow/NodeSettings/NodeSettingsBase.tsx
```

**Analysis documents:**
```
/LAB/@thesis/layra/docs/MCP_CONFIG_DUPLICATION_ANALYSIS.md
/LAB/@thesis/layra/docs/MCP_CONFIG_ANALYSIS_SUMMARY.md
```
