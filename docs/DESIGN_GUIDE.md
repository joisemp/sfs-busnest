# Design System Guide - Registration Detail Page

This document outlines the design patterns, styles, and components used in the registration detail page. Use this as a reference when creating or updating other pages to maintain visual consistency across the application.

---

## 🎨 Color Palette

### Primary Colors (Indigo)
```scss
$indigo-600: #4f46e5  // Primary brand color
$indigo-700: #4338ca  // Darker shade for gradients/hover
$indigo-800: #3730a3  // Darkest shade for active states
```

### Neutral Colors (Slate)
```scss
$slate-50: #f8fafc   // Light backgrounds
$slate-100: #f1f5f9  // Subtle backgrounds
$slate-200: #e2e8f0  // Borders
$slate-700: #334155  // Default text
$slate-800: #1e293b  // Dark text
$slate-900: #0f172a  // Headers
```

### Semantic Colors
```scss
$success: #10b981    // Success states
$warning: #f59e0b    // Warning states
$error: #ef4444      // Error states
$info: #3b82f6       // Informational states
```

---

## 📦 Component Patterns

### 1. Cards

**Standard Card:**
```scss
.card {
  background: white;
  border: 1px solid $slate-200;
  border-radius: 16px;
  padding: 1.5rem;
  transition: all 0.3s ease;
}
```

**Card with Gradient Background:**
```scss
.card-gradient {
  background: linear-gradient(135deg, $indigo-600 0%, $indigo-700 100%);
  border: none;
  border-radius: 16px;
  padding: 1.5rem;
  color: white;
  
  .card-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }
}
```

**Slate Gradient Card:**
```scss
.card-slate-gradient {
  background: linear-gradient(135deg, $slate-800 0%, $slate-900 100%);
  border: none;
  border-radius: 16px;
  padding: 1.5rem;
  color: white;
}
```

**Important:** No shadows on cards - maintain flat design with borders only.

---

### 2. Typography

**Page Headers:**
```scss
.page-header {
  font-size: 2rem;
  font-weight: 700;
  color: $slate-900;
  margin-bottom: 0.5rem;
  line-height: 1.2;
}

.page-subtitle {
  font-size: 1rem;
  color: $slate-700;
  font-weight: 400;
}
```

**Card Titles:**
```scss
.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: $slate-900;
  margin-bottom: 1rem;
}
```

**Body Text:**
```scss
.body-text {
  font-size: 0.9375rem;
  color: $slate-700;
  line-height: 1.6;
}
```

**Small Text:**
```scss
.small-text {
  font-size: 0.875rem;
  color: $slate-700;
}
```

---

### 3. Buttons

**Primary Button:**
```scss
.btn-primary {
  background: linear-gradient(135deg, $indigo-600 0%, $indigo-700 100%);
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 500;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  
  &:hover {
    background: linear-gradient(135deg, $indigo-700 0%, $indigo-800 100%);
    
    i {
      transform: translateX(3px);
    }
  }
  
  i {
    transition: transform 0.3s ease;
  }
}
```

**Secondary Button:**
```scss
.btn-secondary {
  background: white;
  color: $indigo-600;
  border: 1px solid $indigo-600;
  padding: 0.75rem 1.5rem;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 500;
  transition: all 0.3s ease;
  
  &:hover {
    background: $indigo-50;
    border-color: $indigo-700;
    color: $indigo-700;
  }
}
```

**Important:** No box shadows on buttons, use gradients and border effects only.

---

### 4. Spacing System

**Consistent spacing scale (based on 0.25rem / 4px):**

```scss
$space-1: 0.25rem;  // 4px
$space-2: 0.5rem;   // 8px
$space-3: 0.75rem;  // 12px
$space-4: 1rem;     // 16px
$space-5: 1.25rem;  // 20px
$space-6: 1.5rem;   // 24px
$space-8: 2rem;     // 32px
$space-10: 2.5rem;  // 40px
```

**Usage:**
- Between items in lists/grids: `gap: 0.625rem` (10px)
- Card padding: `1.5rem` (24px)
- Section margins: `2rem` (32px)
- Button padding: `0.75rem 1.5rem` (12px 24px)

---

### 5. Border Radius

**Consistent rounding:**
```scss
$radius-sm: 8px;   // Small elements (badges, pills)
$radius-md: 10px;  // Buttons, inputs
$radius-lg: 16px;  // Cards, modals
$radius-xl: 20px;  // Large containers
```

---

## 📊 Chart Styling

### Chart Container
```scss
.chart-container {
  position: relative;
  height: 300px;
  padding: 1rem;
}
```

### Chart.js Configuration Pattern
```javascript
const chartConfig = {
  type: 'bar', // or 'doughnut', 'line', 'horizontalBar'
  data: {
    labels: [...],
    datasets: [{
      data: [...],
      backgroundColor: gradientOrColors,
      borderWidth: 0,
      borderRadius: 8,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          padding: 15,
          font: {
            size: 12,
            weight: '500'
          },
          color: '#334155' // slate-700
        }
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          font: { size: 11 },
          color: '#64748b' // slate-500
        }
      },
      y: {
        grid: { 
          color: '#f1f5f9', // slate-100
          drawBorder: false 
        },
        ticks: {
          font: { size: 11 },
          color: '#64748b'
        }
      }
    }
  }
};
```

### Chart Color Gradients
```javascript
// Bar chart gradient
const gradient = ctx.createLinearGradient(0, 0, 0, 300);
gradient.addColorStop(0, '#6366f1');  // indigo-500
gradient.addColorStop(1, '#4f46e5');  // indigo-600

// Doughnut chart colors (use array for multiple segments)
const colors = ['#4f46e5', '#6366f1', '#818cf8', '#a5b4fc', '#c7d2fe'];
```

---

## 📱 Responsive Design

### Breakpoints
```scss
$mobile: 430px;    // Mobile devices
$tablet: 991px;    // Tablets
$desktop: 1024px;  // Desktop and above
```

### Mobile-First Approach

**Hide complex visualizations on smaller screens:**
```scss
.analytics-section {
  @media screen and (max-width: 991px) {
    display: none;
  }
}
```

**Responsive Grid:**
```scss
.grid-responsive {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
  
  @media screen and (max-width: 991px) {
    grid-template-columns: 1fr;
  }
}
```

**Responsive Typography:**
```scss
.page-header {
  font-size: 2rem;
  
  @media screen and (max-width: 991px) {
    font-size: 1.5rem;
  }
}
```

---

## 🧭 Sidebar Navigation

### Desktop Sidebar
```scss
.sidebar {
  width: 220px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  height: calc(100vh - 60px);
  border-right: 1px solid #e2e8f0;
  
  .nav {
    padding: 1.25rem 0.75rem;
    gap: 0.625rem; // Good spacing between items
  }
  
  .navlink {
    padding: 0.875rem 1rem;
    border-radius: 10px;
    font-weight: 500;
    transition: all 0.2s ease-in-out;
    
    &:hover {
      background: linear-gradient(135deg, rgba(79, 70, 229, 0.08) 0%, rgba(99, 102, 241, 0.12) 100%);
      
      i { transform: scale(1.1); }
      span { transform: translateX(2px); }
    }
  }
  
  .active {
    background: linear-gradient(135deg, $indigo-600 0%, $indigo-700 100%);
    color: white;
    
    &::before {
      content: '';
      position: absolute;
      left: 0;
      width: 4px;
      height: 60%;
      background: white;
      border-radius: 0 4px 4px 0;
    }
  }
}
```

**Important:** No shadows on sidebar or nav items, maintain clean flat design.

---

## 🎯 Animation & Transitions

### Hover Effects
```scss
// Icon scale on hover
i {
  transition: transform 0.2s ease;
  
  &:hover {
    transform: scale(1.1);
  }
}

// Text slide on hover
span {
  transition: transform 0.2s ease;
  
  &:hover {
    transform: translateX(2px);
  }
}

// Button icon slide
.btn i {
  transition: transform 0.3s ease;
}

.btn:hover i {
  transform: translateX(3px);
}
```

**Important Guidelines:**
- **NO transform effects on cards** (no scale, translateY, etc.)
- **NO box shadows** anywhere in the design
- Keep transitions smooth: 0.2s-0.3s duration
- Use `ease` or `ease-in-out` timing

---

## 📋 Layout Patterns

### Page Structure
```html
<div class="main-content">
  <!-- Page Header -->
  <div class="mb-4">
    <h1 class="page-header">Page Title</h1>
    <p class="page-subtitle">Subtitle or description</p>
  </div>
  
  <!-- Analytics/Stats Section (hide on mobile) -->
  <div class="analytics-section mb-4">
    <div class="row g-3">
      <div class="col-md-6">
        <div class="card">
          <!-- Chart or content -->
        </div>
      </div>
    </div>
  </div>
  
  <!-- Main Content Cards -->
  <div class="row g-3">
    <div class="col-lg-6">
      <div class="card">
        <h3 class="card-title">Section Title</h3>
        <!-- Content -->
      </div>
    </div>
  </div>
</div>
```

### Grid System
```scss
// Use Bootstrap grid with custom gap
.row {
  --bs-gutter-x: 1rem;
  --bs-gutter-y: 1rem;
}

// Or use CSS Grid
.custom-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}
```

---

## 🎨 Gradient Patterns

### Background Gradients
```scss
// Primary Indigo Gradient
background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);

// Slate Dark Gradient
background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);

// Light Background Gradient
background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);

// Hover State Gradient (lighter)
background: linear-gradient(135deg, rgba(79, 70, 229, 0.08) 0%, rgba(99, 102, 241, 0.12) 100%);
```

### Chart Gradients
```javascript
// Vertical gradient for bars
const gradient = ctx.createLinearGradient(0, 0, 0, chartHeight);
gradient.addColorStop(0, '#6366f1');
gradient.addColorStop(1, '#4f46e5');

// Radial gradient for doughnut (if needed)
const radialGradient = ctx.createRadialGradient(
  centerX, centerY, 0,
  centerX, centerY, radius
);
radialGradient.addColorStop(0, '#6366f1');
radialGradient.addColorStop(1, '#4f46e5');
```

---

## 📊 Data Visualization Best Practices

### Chart Types Selection
- **Bar Chart**: Comparing categories (routes, stops, institutions)
- **Horizontal Bar**: Long labels (top pickup/drop points)
- **Doughnut Chart**: Part-to-whole relationships (ticket type distribution)
- **Line Chart**: Time series data (avoid for non-temporal data)

### Colors for Multiple Series
```javascript
const seriesColors = {
  primary: '#4f46e5',   // Pickup/Main
  secondary: '#6366f1',  // Drop/Secondary
  tertiary: '#818cf8',   // Additional series
  quaternary: '#a5b4fc', // Fourth series
  quinary: '#c7d2fe'     // Fifth series
};
```

### Accessibility
- Always include legends for multi-series charts
- Use sufficient color contrast
- Provide `aria-label` for chart containers
- Include data table alternative for screen readers

---

## ✅ Do's and Don'ts

### ✅ Do's
- Use indigo gradients for primary elements
- Maintain consistent border-radius (8px, 10px, 16px)
- Use 0.625rem gap between navigation items
- Implement smooth transitions (0.2s-0.3s)
- Hide complex visualizations on mobile (≤991px)
- Use flat design with borders, no shadows
- Apply hover effects on interactive elements
- Use proper semantic HTML
- Follow spacing system consistently

### ❌ Don'ts
- Don't use box shadows anywhere
- Don't use transform scale/translateY on cards
- Don't show analytics/charts on mobile devices
- Don't use random colors outside the palette
- Don't mix different border-radius values
- Don't forget responsive breakpoints
- Don't use heavy animations
- Don't add unnecessary complexity

---

## 🔧 Implementation Checklist

When creating a new page with this design system:

- [ ] Import color variables from `base/_colors.scss`
- [ ] Use card component pattern with 16px border-radius
- [ ] Apply gradient backgrounds for primary sections
- [ ] Implement responsive grid layout
- [ ] Add hover effects on interactive elements (no transform on cards)
- [ ] Hide analytics/complex visuals on mobile (≤991px)
- [ ] Use consistent spacing (0.625rem gaps, 1.5rem padding)
- [ ] Apply typography hierarchy (page-header, card-title, body-text)
- [ ] Test on all breakpoints (mobile, tablet, desktop)
- [ ] Ensure no shadows are present
- [ ] Verify all transitions are smooth (0.2s-0.3s)
- [ ] Check color contrast for accessibility

---

## 📁 File References

### Key Files
- **SCSS Variables**: `src/static/styles/base/_colors.scss`
- **Sidebar Styles**: `src/static/styles/_sidebar_navbar_base.scss`
- **Page Styles**: `src/static/styles/central_admin/registration_detail/style.scss`
- **Template**: `src/templates/central_admin/registration_detail.html`
- **Views**: `src/services/views/central_admin.py` (RegistrationDetailView)

### Compilation
```powershell
# Compile individual SCSS file
cd src/static/styles/central_admin/registration_detail
sass style.scss style.css

# Compile sidebar base
cd src/static/styles
sass _sidebar_navbar_base.scss _sidebar_navbar_base.css
```

---

## 🎓 Learning Resources

### Color Theory
- Primary color (indigo) for brand identity and CTAs
- Neutral colors (slate) for text and subtle backgrounds
- Use gradients to add depth without shadows

### Layout Principles
- Mobile-first responsive design
- Progressive disclosure (hide complexity on small screens)
- Grid-based layouts for consistency

### Animation Guidelines
- Subtle micro-interactions (icon scale, text slide)
- No distracting animations
- Smooth transitions for state changes

---

## 📝 Notes for AI Assistants

When asked to apply this design to other pages:

1. **Read this guide first** before making design decisions
2. **Match the exact color values** - don't approximate
3. **Follow the spacing system** - use defined increments
4. **No shadows** - this is a flat design system
5. **Mobile optimization** - always hide charts/analytics on ≤991px
6. **Sidebar spacing** - use 0.625rem gap between items
7. **Button icons** - always add hover animation (translateX)
8. **Card transforms** - NEVER apply scale/translateY to cards
9. **Test responsiveness** - verify all breakpoints
10. **Maintain consistency** - use same patterns everywhere

---

**Last Updated**: February 27, 2026  
**Version**: 1.0  
**Based On**: Registration Detail Page Design System
