### 1. User goal
Manage user profiles, specifically selecting the profile of the user who is watching.

### 2. Roles
The following roles are observed to interact with the profiles capability:
- Guest
- Member
- Premium

### 3. Flow per role
#### Guest
1. Enters the `/profiles` route.
2. Sees the "Who's watching?" screen with options like "🍿 Sam Member" and "🧸 Kids".
3. Selects a profile (e.g., "🍿 Sam Member").
4. Exits into the `/browse` capability.

#### Member
1. Enters the `/profiles` route.
2. Sees the "Who's watching?" screen with options like "🍿 Sam Member" and "🧸 Kids".
3. Selects a profile (e.g., "🍿 Sam Member").
4. Exits into either the `/browse` capability or the `/account/plan` capability.

#### Premium
1. Enters the `/profiles` route.
2. Sees the "Who's watching?" screen with options like "🍿 Pat Premium" and "🧸 Kids".
3. Selects a profile (e.g., "🍿 Pat Premium").
4. Exits into either the `/browse` capability or the `/account/plan` capability.

### 4. Success criteria
- The user is able to select their profile from the list of available profiles.
- The user is redirected to the correct capability after selecting their profile (e.g., `/browse` or `/account/plan`).

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The profiles capability depends on the following capabilities:
- `/browse`
- `/account/plan`

### 7. Implicit metric
The number of successful profile selections, potentially measured by the number of exits into the `/browse` or `/account/plan` capabilities from the profiles capability.