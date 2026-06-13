### 1. User goal
Manage my list of saved content, as indicated by the copy "Saved for later" on the `/my-list` screens.

### 2. Roles
The observed user roles for this capability are:
- member
- premium

### 3. Flow per role
Both member and premium roles can access the `/my-list` screens. The flow involves:
- Entering the `/my-list` screen, which displays the user's saved content.
- Clicking the 'Accept' button to transition between different `/my-list` screens (e.g., from `/my-list::s7709ba` to `/my-list::s329ed6`).
- Navigating to other capabilities via links, such as 'STREAMLY', 'Browse', 'Search', 'Kids', and the user's account link.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The my_list capability depends on the following capabilities:
- `/browse`
- `/search`
- `/kids`
- `/account`
- The capability for signing out (`/::sfb8cd5` or `/::scdffb1`)

These dependencies are observed through the links and buttons on the `/my-list` screens that navigate to these other capabilities.

### 7. Implicit metric
The usage of the 'Saved for later' feature, as indicated by the copy on the `/my-list` screens, could be an implicit metric for measuring user engagement with the my_list capability. Additionally, the frequency of transitions between different `/my-list` screens and the navigation to other capabilities from the `/my-list` screens might also serve as implicit metrics.