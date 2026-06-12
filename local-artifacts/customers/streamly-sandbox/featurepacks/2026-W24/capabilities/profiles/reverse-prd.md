### 1. User goal
Manage user profiles and settings, specifically selecting the profile of the user who is watching.

### 2. Roles
The following roles are observed to interact with the profiles capability:
- Guest
- Member
- Premium

### 3. Flow per role
- **Guest**: The guest role is presented with a screen that asks "Who's watching?" and provides options such as "🍿 Sam Member" and "🧸 Kids". Upon selecting an option, the guest is redirected to the `/browse` capability.
- **Member**: The member role is presented with a similar "Who's watching?" screen. Selecting an option redirects the member to either the `/browse` capability or the `/account/plan` capability.
- **Premium**: The premium role also sees the "Who's watching?" screen with options like "🍿 Pat Premium" and "🧸 Kids". Upon selection, the premium user is redirected to either the `/browse` capability or the `/account/plan` capability.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The profiles capability depends on or exits into the following capabilities:
- `/browse` capability: Accessed after selecting a profile.
- `/account/plan` capability: Accessed by member and premium roles after selecting a profile, potentially for managing their account plans.

### 7. Implicit metric
_(no evidence observed)_