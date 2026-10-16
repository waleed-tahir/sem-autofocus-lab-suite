# Dark Matte UI — Design System & Specification Guide

## 1. Executive Summary & Design Philosophy

This design language is rooted in **Neo-Metro / Early Fluent Minimalism**. It strips away decorative UI chrome—such as button containers, drop shadows, heavy borders, and skeuomorphic gradients—in favor of **typographic hierarchy, spatial grouping, and stark matte contrast**.

Whether building a media player, a RAW image processing suite, a code editor, or a developer utility, every application in the ecosystem must adhere to three foundational pillars:

1. **Chromeless Immersion:** The application window merges seamlessly with its content. Window management controls (`Minimize`, `Maximize`, `Close`) float directly on the primary canvas with zero title-bar divider.

2. **Surface Depth via Materiality, Not Shadows:** Elevation is communicated through subtle luminance shifts and frosted background translucency (Acrylic sidebar) rather than drop shadows or strokes.

3. **Wireframe Action Language:** Interactive controls, parameter sliders, and tools dispense with pill or box backgrounds. They rely on razor-sharp $1\text{px}$ stroke iconography and precise typographic labels.

## 2. Color System & Surface Tokens

The palette is intentionally desaturated across surfaces so that user content (photography, code, data visualizations, charts) commands $100\%$ of the visual energy.

### 2.1 Surface & Background Tokens

| Token Name | Hex Code | RGBA / Opacity | Usage & Specification | 
| ----- | ----- | ----- | ----- | 
| `--bg-canvas-primary` | `#181819` | `rgb(24, 24, 25)` | Main application workspace background. Completely opaque, non-reflective matte charcoal. | 
| `--bg-sidebar-acrylic` | `#242527` | `rgba(36, 37, 39, 0.82)` | Left navigation rail. Should utilize a backdrop blur (`backdrop-filter: blur(24px)`) with a subtle $2\%$ white noise texture if supported by the OS. | 
| `--bg-surface-hover` | `#2A2B2E` | `rgba(255, 255, 255, 0.05)` | Subtle row highlight when hovering over list items, layers, or parameter rows. | 
| `--bg-surface-active` | `#323337` | `rgba(255, 255, 255, 0.09)` | Pressed or selected row state in tables and tool panels. | 
| `--border-subtle` | `#2E2F33` | `rgba(255, 255, 255, 0.08)` | Used only when strictly necessary (e.g., slider tracks or subtle section dividers). | 

### 2.2 Typography & Iconography Tokens

| Token Name | Hex Code | Opacity Equivalent | Usage & Specification | 
| ----- | ----- | ----- | ----- | 
| `--text-primary` | `#FFFFFF` | $100\%$ White | Main headers, active navigation labels, primary list titles, active icons. | 
| `--text-secondary` | `#9A9B9E` | $60\%$ White | Descriptions, metadata, technical parameters, inactive sidebar labels. | 
| `--text-muted` | `#6E7074` | $42\%$ White | Timestamps, index numbers, disabled controls, secondary units. | 

### 2.3 Brand & Semantic Accent Tokens

| Token Name | Hex Code | Usage Rule | 
| ----- | ----- | ----- | 
| `--accent-cyan` | `#00C3F9` | **Micro-Accent Only.** Used exclusively for: (1) The $3\text{px} \times 18\text{px}$ vertical active indicator bar in the sidebar, (2) Inline expansion links (`MORE`, `RESET`), and (3) Active slider node highlights. **Never** use as a large button fill or banner background. | 
| `--accent-cyan-hover` | `#40D4FF` | Hover state for inline cyan text actions. | 
| `--status-warning` | `#F5A623` | Non-intrusive indicator for clipping/warnings in utility apps. | 
| `--status-danger` | `#E81123` | Used only on the top-right window `Close (X)` button hover state or destructive action confirmation. | 

## 3. Typography & Hierarchy

The typographic voice is clean, humanist sans-serif. It relies on dramatic size contrast between the Hero Title and the surrounding metadata.

* **Primary Font Family:** `Segoe UI`, `Inter`, or `SF Pro Display` (System Native Sans-Serif).

* **Numeric Discipline:** Always enable `font-variant-numeric: tabular-nums` for metrics, index numbers, pixel dimensions, and slider values so columns align vertically with mathematical precision.

### 3.1 Type Scale Specification

| Style Role | Font Size | Line Height | Weight | Color Token | Tracking | Context / Usage | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| **Hero Title (H1)** | $42\text{px}$ | $48\text{px}$ | Bold ($700$) | `--text-primary` | $-0.02\text{em}$ | Primary subject title (`Kakoi Miku`, `IMG_8492.CR3`, `Project Alpha`). | 
| **Section Header (H2)** | $15\text{px}$ | $20\text{px}$ | Semibold ($600$) | `--text-primary` | $0\text{em}$ | Column and module headers (`In Library`, `Adjustments`, `Layers`). | 
| **Card / Feature Title (H3)** | $14\text{px}$ | $18\text{px}$ | Semibold ($600$) | `--text-primary` | $0\text{em}$ | Featured sub-item title (`Supercell`, `Preset: Kodak Gold`). | 
| **List / Row Primary** | $13\text{px}$ | $18\text{px}$ | Semibold ($600$) | `--text-primary` | $0\text{em}$ | Item titles, adjustment slider names (`Contrast`, `Exposure`), active sidebar items. | 
| **Body / Bio Copy** | $13\text{px}$ | $19\text{px}$ | Regular ($400$) | `--text-secondary` | $+0.01\text{em}$ | Multi-line descriptive blocks, file notes. Max width: $320\text{px}$. | 
| **Metadata / Secondary** | $13\text{px}$ | $18\text{px}$ | Regular ($400$) | `--text-secondary` | $0\text{em}$ | Secondary table columns, inactive sidebar items, subtitle beneath thumbnails. | 
| **Micro / Inline Link** | $11\text{px}$ | $18\text{px}$ | Semibold ($600$) | `--accent-cyan` | $+0.04\text{em}$ | Uppercase inline triggers (`MORE`, `APPLY`, `RAW`). | 

## 4. Layout Architecture & Spatial Grid

All applications built with this design language share a unified **Three-Zone Desktop Architecture** based on an $8\text{px}$ spatial grid.

```
+-------------------+----------------------------------------------------+--------------------+
|  LEFT NAV RAIL    |  PRIMARY WORKSPACE                                 |  WINDOW CONTROLS   |
|  (Width: 240px)   |  (Fluid Flex-1, Left Padding: 48px)                |  (-  []  X)        |
|                   |                                                    |                    |
|  App Title        |  [ HERO HEADER ZONE ]                              |                    |
|  [Hamburger]      |   H1 Title          Secondary Metadata             |                    |
|                   |   Description block [Action Icons]                 |                    |
|  Search           |                                                    |                    |
|                   |----------------------------------------------------+--------------------|
|  (o) Nav Item 1   |  [ PRIMARY CONTENT ZONE ]                          | [ CONTEXT RAIL ]   |
|  (o) Nav Item 2   |  Section Header ("In Library" / "Adjustments")     | Section Header     |
| |[o] Active Item  |                                                    | ("Presets" /       |
|  (o) Nav Item 4   |  1  Row Title                Meta            Value |  "History")        |
|                   |  2  Row Title                Meta            Value | [64x64] Title      |
|  ---------------- |  3  Row Title                Meta            Value |         Subtitle   |
|  Section Subhead  |  4  Row Title                Meta            Value | [64x64] Title      |
+-------------------+----------------------------------------------------+--------------------+
```

### 4.1 Zone 1: Left Navigation Rail (`240px` Fixed)

* **Width:** $240\text{px}$ expanded (collapses to $48\text{px}$ icon-only rail on narrow viewports).

* **Padding:** $16\text{px}$ top/bottom, $16\text{px}$ left/right.

* **Row Height:** $40\text{px}$ per navigation item.

* **Icon-to-Label Gap:** $16\text{px}$ horizontal spacing between the $16\text{px} \times 16\text{px}$ wireframe icon and the text label.

* **Active State Anatomy:**

  * A $3\text{px}$ wide by $16\text{px}$ tall solid `--accent-cyan` vertical bar anchored $4\text{px}$ from the left edge of the sidebar.

  * Text transitions from `--text-secondary` (Regular) to `--text-primary` (Semibold).

  * No full-row background pill is shown unless actively hovered.

### 4.2 Zone 2: Hero Header Zone (Top of Primary Workspace)

* **Top Margin:** $36\text{px}$ from top window edge.

* **Left Margin:** $48\text{px}$ from the Left Navigation Rail border.

* **Flexible Header Layout:** The header relies purely on typographic hierarchy (H1 Title + metadata/description block) rather than a mandatory profile image or feature show. If an application requires a visual asset (such as an image thumbnail or document preview), it uses a strict $0\text{px}$ radius rectangular container rather than a circle.

* **Header Action Cluster:** Positioned on the right side of the header area. Displays a secondary classification label above a horizontal row of $16\text{px}$ wireframe action icons spaced $24\text{px}$ apart.

### 4.3 Zone 3: Lower Split Workspace (Primary List + Right Context Rail)

* **Vertical Offset:** Starts $40\text{px}$ below the Hero Header Zone.

* **Primary Content Column (Left, Fluid** $65\%–70\%$ **width):**

  * Houses structured rows (tracks, image adjustment sliders, code editors, or layer stacks).

  * Row height: $36\text{px}$ to $40\text{px}$, zero horizontal divider lines. Visual separation is achieved purely through vertical whitespace and strict column alignment.

* **Right Context Rail (Right, Fixed** $260\text{px}–300\text{px}$ **width):**

  * Separated from the Primary Content Column by a minimum $48\text{px}$ gutter.

  * Features a vertical stack of square media/preset items ($64\text{px} \times 64\text{px}$ thumbnail on the left, $12\text{px}$ gap, vertically centered two-line title + subtitle on the right). Vertical gap between stacked cards is $12\text{px}$.

## 5. Geometry, Corner Radii & Iconography Rules

### 5.1 The Corner Radius Law

To preserve the signature crispness of this interface, designers must avoid decorative rounding:

* $0\text{px}$ **Radius (Sharp Squares/Rectangles):** **Mandatory** for all cards, thumbnails, input boxes, panels, hover highlight bars, tooltips, and dialogs.

* **No Circular Mandate:** Circular containers ($50\%$ radius) are removed as a required layout anchor. All UI components strictly adhere to rectilinear ($0\text{px}$) geometry to maintain a clean, utility-grade aesthetic.

### 5.2 Iconography & Chromeless Controls

* **Stroke Weight:** Strictly $1\text{px}$ or $1.25\text{px}$ uniform stroke width on a $16\text{px} \times 16\text{px}$ pixel grid.

* **Fill Rule:** Icons are always hollow/wireframe outlines. Never use solid filled icons.

* **No Button Containers:** Action buttons in headers and sub-headers do **not** have boxes, borders, or pill backgrounds by default.

  * **Default State:** `#FFFFFF` at $85\%$ opacity, bare icon.

  * **Hover State:** `#FFFFFF` at $100\%$ opacity, optional subtle square hover target ($32\text{px} \times 32\text{px}$ at `rgba(255,255,255,0.06)`).

  * **Pressed State:** Scales down to $92\%$ (`transform: scale(0.92)`).

## 6. Cross-Application Adaptation Guide (Image Processing App Example)

When applying this design system to a non-media utility—such as a **Professional RAW Image Processor or Photo Editor**—the structural skeleton remains $100\%$ identical while components map to utility functions:

### 6.1 Component Mapping Matrix

| Design System Slot | Music App (Reference) | Image Processing App (Adaptation) | 
| ----- | ----- | ----- | 
| **Left Nav Rail** | `Your Groove`, `Explore`, `Albums`, `Artists` | `Import`, `Develop / Adjustments`, `Color Grading`, `Layers`, `History`, `Export` | 
| **Hero Title (H1)** | Artist Name (`Kakoi Miku`) | Active File Name (`Image_104.RAW`) | 
| **Hero Bio Block** | Artist biography + `MORE` link | Camera & EXIF telemetry (`Sony A7R V • 35mm f/1.4 • ISO 100`) + `METADATA` link | 
| **Header Action Cluster** | Genre tag + Action Icons | Color Space tag (`AdobeRGB • 16-Bit`) + Utility Action Icons | 
| **Numbered Table Rows** | `1  Iroha   Kakoi Miku   6:59` | `1  Exposure    [-------o-------]   +0.45` | 
| **Right Context Rail** | `Mixtapes` ($64\text{px}$ square art + Title) | `Presets & LUTs` ($64\text{px}$ square preview + Preset Name) | 

### 6.2 Custom Utility Controls (Sliders, Toggles & Inputs)

To ensure utility controls match the flat wireframe aesthetic:

* **Adjustment Sliders:**

  * **Track:** $2\text{px}$ height, solid `#38393D` (`rgba(255,255,255,0.15)`), $0\text{px}$ border radius.

  * **Thumb (Handle):** A crisp vertical rectangular bar ($3\text{px}$ wide $\times$ $14\text{px}$ tall) in solid `#FFFFFF`, transitioning to `--accent-cyan` (`#00C3F9`) while actively dragging.

* **Collapsible Parameter Groups:**

  * Group headers (`Light`, `Color`, `Detail`) use `#222326` subtle flat band headers ($28\text{px}$ height) with $13\text{px}$ Semibold white text.

## 7. Designer Checklist (Do's & Don'ts)

### ✅ DO

* **Do** maintain generous negative space around the Hero Header ($48\text{px}$ left margin, $36\text{px}$ top margin).

* **Do** keep every thumbnail and container strictly rectangular with $0\text{px}$ border radius.

* **Do** use typographic weight and opacity (`#FFFFFF` Semibold vs. `#9A9B9E` Regular) to establish data hierarchy.

* **Do** limit `--accent-cyan` (`#00C3F9`) to less than $2\%$ of the total screen surface area.

### ❌ DON'T

* **Don't** use circular profile images, avatar bubbles, or feature show containers as mandatory layout anchors.

* **Don't** add pill-shaped buttons, rounded cards ($8\text{px}$ radius), or drop shadows behind components.

* **Don't** use heavy $2\text{px}+$ solid filled icons; stick strictly to $1\text{px}$ wireframe geometry.

* **Don't** place a traditional OS title bar at the top; integrate window controls directly into the top-right corner of the canvas.