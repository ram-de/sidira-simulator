### 1. User goal
The user goal is to view and manage their list of content on Streamly, as indicated by the presence of the "My List" heading and the "Saved for later" copy on the `/my-list` screens.

### 2. Roles
The observed user roles are:
* Member
* Premium

### 3. Flow per role
Both member and premium roles can access the `/my-list` screens. The flow for both roles involves:
1. Viewing the "My List" screen with headings and copy, including "STREAMLY", "Browse", "Search", "My List", "Kids", and the user's name ("Sam Member" or "Pat Premium").
2. Clicking the "Accept" button to transition between `/my-list` screens (e.g., from `/my-list::s7709ba` to `/my-list::s329ed6`).
There is no observed difference in the flow between member and premium roles, except for the link text "Sam Member" vs "Pat Premium" which leads to the `/account` screen.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The `/my-list` capability has dependencies on the following capabilities:
* `/browse` (exits from `/my-list::s7709ba` and `/my-list::s329ed6` via "STREAMLY" and "Browse" links)
* `/search` (exits from `/my-list::s7709ba` and `/my-list::s329ed6` via "Search" link)
* `/kids` (exits from `/my-list::s7709ba` and `/my-list::s329ed6` via "Kids" link)
* `/account` (exits from `/my-list::s7709ba` and `/my-list::s329ed6` via the user's name link)
* Sign-out functionality (exits from `/my-list::s7709ba` and `/my-list::s329ed6` via "Sign Out" button)

### 7. Implicit metric
_(no evidence observed)_