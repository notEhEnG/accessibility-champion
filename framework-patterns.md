# Framework A11y Patterns

## Contents
1. [React / JSX](#react--jsx)
2. [Vue SFC](#vue-sfc)
3. [Angular](#angular)
4. [Svelte](#svelte)
5. [Common Widgets](#common-widgets)

---

## React / JSX

### Accessible icon-only button
```jsx
// Bad
<button onClick={handleClose}><Icon name="x" /></button>

// Good
<button onClick={handleClose} aria-label="Close dialog">
  <Icon name="x" aria-hidden="true" />
</button>
```

### Form with full label association and error
```jsx
function EmailField({ error }) {
  const errorId = 'email-error'
  return (
    <div>
      <label htmlFor="email">
        Email address
        <span aria-hidden="true"> *</span>
        <span className="sr-only"> (required)</span>
      </label>
      <input
        id="email"
        type="email"
        required
        aria-required="true"
        aria-invalid={!!error}
        aria-describedby={error ? errorId : undefined}
        autoComplete="email"
      />
      {error && (
        <p id={errorId} role="alert" className="error">
          {error}
        </p>
      )}
    </div>
  )
}
```

### Accessible modal / dialog
```jsx
import { useEffect, useRef } from 'react'
import FocusTrap from 'focus-trap-react'   // or implement manually

function Modal({ isOpen, onClose, title, children }) {
  const closeRef = useRef(null)

  // Return focus to trigger on close
  const triggerRef = useRef(null)
  useEffect(() => {
    if (!isOpen) triggerRef.current?.focus()
  }, [isOpen])

  if (!isOpen) return null

  return (
    <FocusTrap>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <h2 id="modal-title">{title}</h2>
        {children}
        <button ref={closeRef} onClick={onClose} aria-label="Close dialog">
          ×
        </button>
      </div>
    </FocusTrap>
  )
}
```

### Accessible tabs
```jsx
function Tabs({ tabs }) {
  const [activeIndex, setActiveIndex] = useState(0)

  const handleKeyDown = (e, index) => {
    if (e.key === 'ArrowRight') setActiveIndex((index + 1) % tabs.length)
    if (e.key === 'ArrowLeft') setActiveIndex((index - 1 + tabs.length) % tabs.length)
    if (e.key === 'Home') setActiveIndex(0)
    if (e.key === 'End') setActiveIndex(tabs.length - 1)
  }

  return (
    <div>
      <div role="tablist" aria-label="Content sections">
        {tabs.map((tab, i) => (
          <button
            key={tab.id}
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={i === activeIndex}
            aria-controls={`panel-${tab.id}`}
            tabIndex={i === activeIndex ? 0 : -1}
            onClick={() => setActiveIndex(i)}
            onKeyDown={(e) => handleKeyDown(e, i)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab, i) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`panel-${tab.id}`}
          aria-labelledby={`tab-${tab.id}`}
          hidden={i !== activeIndex}
        >
          {tab.content}
        </div>
      ))}
    </div>
  )
}
```

### Skip link (add as very first element in App)
```jsx
function SkipLink() {
  return (
    <a
      href="#main-content"
      className="skip-link"  // see CSS below
    >
      Skip to main content
    </a>
  )
}

/* CSS */
.skip-link {
  position: absolute;
  top: -9999px;
  left: 1rem;
  padding: 0.5rem 1rem;
  background: #000;
  color: #fff;
  z-index: 9999;
  text-decoration: none;
}
.skip-link:focus {
  top: 1rem;
}
```

### Toast / notification (live region)
```jsx
function ToastContainer({ messages }) {
  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      aria-relevant="additions"
      className="toast-container"
    >
      {messages.map(msg => (
        <div key={msg.id} role="status">
          {msg.text}
        </div>
      ))}
    </div>
  )
}
```

---

## Vue SFC

### Form field with label and error
```vue
<template>
  <div>
    <label :for="id">
      {{ label }}
      <span v-if="required" aria-hidden="true"> *</span>
    </label>
    <input
      :id="id"
      :type="type || 'text'"
      :required="required"
      :aria-required="required"
      :aria-invalid="!!error"
      :aria-describedby="error ? `${id}-error` : undefined"
    />
    <p
      v-if="error"
      :id="`${id}-error`"
      role="alert"
    >{{ error }}</p>
  </div>
</template>
```

### Accessible disclosure / accordion
```vue
<template>
  <div>
    <button
      :aria-expanded="isOpen"
      :aria-controls="`panel-${id}`"
      @click="toggle"
    >
      {{ title }}
    </button>
    <div
      :id="`panel-${id}`"
      :hidden="!isOpen"
    >
      <slot />
    </div>
  </div>
</template>
```

---

## Angular

### Form control with reactive forms
```typescript
// component.ts
this.form = this.fb.group({
  email: ['', [Validators.required, Validators.email]]
})
get emailError() {
  const ctrl = this.form.get('email')
  if (ctrl?.errors?.required) return 'Email is required'
  if (ctrl?.errors?.email) return 'Enter a valid email address'
  return null
}
```

```html
<!-- template -->
<label for="email">Email address</label>
<input
  id="email"
  type="email"
  formControlName="email"
  [attr.aria-invalid]="!!emailError"
  [attr.aria-describedby]="emailError ? 'email-error' : null"
  autocomplete="email"
/>
<p *ngIf="emailError" id="email-error" role="alert">{{ emailError }}</p>
```

---

## Svelte

### Accessible combobox / autocomplete
```svelte
<script>
  let value = ''
  let suggestions = []
  let activeIndex = -1
  let listboxId = 'combo-listbox'

  function handleKeydown(e) {
    if (e.key === 'ArrowDown') activeIndex = Math.min(activeIndex + 1, suggestions.length - 1)
    if (e.key === 'ArrowUp') activeIndex = Math.max(activeIndex - 1, 0)
    if (e.key === 'Escape') { suggestions = []; activeIndex = -1 }
    if (e.key === 'Enter' && activeIndex >= 0) selectSuggestion(suggestions[activeIndex])
  }
</script>

<div role="combobox" aria-expanded={suggestions.length > 0} aria-haspopup="listbox">
  <input
    type="text"
    bind:value
    aria-autocomplete="list"
    aria-controls={listboxId}
    aria-activedescendant={activeIndex >= 0 ? `option-${activeIndex}` : undefined}
    on:keydown={handleKeydown}
  />
  {#if suggestions.length > 0}
    <ul role="listbox" id={listboxId}>
      {#each suggestions as s, i}
        <li
          role="option"
          id="option-{i}"
          aria-selected={i === activeIndex}
          on:click={() => selectSuggestion(s)}
        >{s.label}</li>
      {/each}
    </ul>
  {/if}
</div>
```

---

## Common Widgets

### Tooltip (accessible — not CSS-only)
CSS-only tooltips using `:hover` are inaccessible. Use:
```jsx
// Show on focus AND hover; reference with aria-describedby
function Tooltip({ id, content, children }) {
  const [visible, setVisible] = useState(false)
  return (
    <span style={{ position: 'relative' }}>
      {React.cloneElement(children, {
        'aria-describedby': id,
        onMouseEnter: () => setVisible(true),
        onMouseLeave: () => setVisible(false),
        onFocus: () => setVisible(true),
        onBlur: () => setVisible(false),
      })}
      <span
        id={id}
        role="tooltip"
        style={{ visibility: visible ? 'visible' : 'hidden' }}
      >
        {content}
      </span>
    </span>
  )
}
```

### Data table
```html
<table>
  <caption>Monthly sales figures by region</caption>
  <thead>
    <tr>
      <th scope="col">Month</th>
      <th scope="col">North</th>
      <th scope="col">South</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">January</th>
      <td>$12,000</td>
      <td>$9,000</td>
    </tr>
  </tbody>
</table>
```

### Loading state (spinner)
```html
<!-- Bad: spinner with no text alternative -->
<div class="spinner"></div>

<!-- Good -->
<div role="status" aria-live="polite" aria-label="Loading">
  <div class="spinner" aria-hidden="true"></div>
  <span class="sr-only">Loading, please wait…</span>
</div>
```

### sr-only utility class (copy this into your global CSS)
```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
  border: 0;
}
```
