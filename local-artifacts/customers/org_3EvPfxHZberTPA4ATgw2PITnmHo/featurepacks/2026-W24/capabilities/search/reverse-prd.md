### 1. User goal
Search for specific content on Streamly.

### 2. Roles
The observed roles are:
- member
- premium

### 3. Flow per role
Both member and premium roles have the same flow:
1. Access the search screen (`/search::sf0043e` or `/search::se78740`).
2. View headings and copy, including "Search", "STREAMLY", "Browse", "My List", "Kids", and the user's name ("Sam Member" or "Pat Premium").
3. Optionally, click on links to navigate to other screens, such as:
   - `/browse` by clicking "STREAMLY" or "Browse".
   - `/my-list` by clicking "My List".
   - `/kids` by clicking "Kids".
   - `/account` by clicking the user's name.
   - `/title/:id` by clicking on a title link (e.g., "/title/t-108").
   - Sign out by clicking the "Sign Out" button.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The search capability depends on the following capabilities:
- `/browse`
- `/my-list`
- `/kids`
- `/account`
- `/title/:id`
- Sign out functionality (`/::sfb8cd5` or `/::scdffb1`)

### 7. Implicit metric
_(no evidence observed)_