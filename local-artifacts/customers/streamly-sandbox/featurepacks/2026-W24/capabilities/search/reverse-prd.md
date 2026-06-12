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
3. The user can click on various links to exit the search capability, such as "STREAMLY", "Browse", "My List", "Kids", their name, or "Sign Out".
4. The user can also click on title links (e.g., "/title/t-108") to view more information about a specific title.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The search capability exits into the following capabilities:
- Browse (`/browse::s2c425e` or `/browse::s2ae585`)
- My List (`/my-list::s7709ba` or `/my-list::s329ed6`)
- Kids (`/kids::s7709ba` or `/kids::s329ed6`)
- Account (`/account::s4058eb` or `/account::saca983`)
- Title details (`/title/:id::overlay+dialog+s0910b3` or `/title/:id::overlay+dialog+s1b7577`)
- Sign Out (`/::sfb8cd5` or `/::scdffb1`)

### 7. Implicit metric
_(no evidence observed)_