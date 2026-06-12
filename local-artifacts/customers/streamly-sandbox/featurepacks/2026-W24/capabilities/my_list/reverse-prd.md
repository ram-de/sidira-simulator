### 1. User goal
View and manage my list of saved content.

### 2. Roles
The following roles are observed to interact with the "my_list" capability:
- member
- premium

### 3. Flow per role
Both member and premium roles can access the "my_list" capability through the `/my-list` route. The flow involves:
- Entering the `/my-list` screen, which displays the "My List" heading and "Saved for later" copy.
- Navigating between different states of the `/my-list` screen (e.g., `s7709ba` and `s329ed6`) by clicking the 'Accept' button.
- Both roles can exit the "my_list" capability into other capabilities, such as "browse", "search", "kids", and "account", by clicking on the corresponding links.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The "my_list" capability has dependencies on the following capabilities:
- "browse"
- "search"
- "kids"
- "account"

These dependencies are observed through the exit transitions from the "my_list" capability to these other capabilities.

### 7. Implicit metric
_(no evidence observed)_