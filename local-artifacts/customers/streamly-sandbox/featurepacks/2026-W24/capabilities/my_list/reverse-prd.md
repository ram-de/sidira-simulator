### 1. User goal
The user goal is to manage and view saved content on Streamly, as indicated by the copy "Saved for later" on the `/my-list` screens.

### 2. Roles
The observed roles are:
* member
* premium

### 3. Flow per role
Both member and premium roles can access the `/my-list` screens. The flow for both roles involves:
1. Viewing the `/my-list` screen with the heading "My List" and copy "Saved for later".
2. Clicking the 'Accept' button to transition between `/my-list::s7709ba` and `/my-list::s329ed6`.
Both roles can also exit the `/my-list` capability into other capabilities, such as `/browse`, `/search`, `/kids`, and `/account`.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The `/my-list` capability depends on the following capabilities:
* `/browse`: linked from `/my-list` via "STREAMLY" and "Browse" links.
* `/search`: linked from `/my-list` via the "Search" link.
* `/kids`: linked from `/my-list` via the "Kids" link.
* `/account`: linked from `/my-list` via the user's name link ("Sam Member" or "Pat Premium").
* Authentication/Authorization: the presence of a "Sign Out" button suggests that the user must be signed in to access the `/my-list` capability.

### 7. Implicit metric
_(no evidence observed)_