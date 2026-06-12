### 1. User goal
The user goal is to select a profile to use with Streamly, as indicated by the copy "Who's watching?" on the `/profiles` screen.

### 2. Roles
The observed user roles are:
* Guest
* Member
* Premium

### 3. Flow per role
* **Guest**: The guest role sees the `/profiles::chooser+sab6eb8` and `/profiles::chooser+s157f95` screens, with the heading "Who's watching?" and options including "🍿 Sam Member" and "🧸 Kids". Selecting the first option takes them to the `/browse` capability.
* **Member**: The member role sees the `/profiles::chooser+sab6eb8` and `/profiles::chooser+s157f95` screens, with the heading "Who's watching?" and options including "🍿 Sam Member" and "🧸 Kids". Selecting the first option takes them to either the `/browse` capability or the `/account/plan` capability.
* **Premium**: The premium role sees the `/profiles::chooser+se8c8c0` and `/profiles::chooser+sdb9b57` screens, with the heading "Who's watching?" and options including "🍿 Pat Premium" and "🧸 Kids". Selecting the first option takes them to either the `/browse` capability or the `/account/plan` capability.

### 4. Success criteria
_(no evidence observed)_

### 5. Edge cases & failure modes
_(no evidence observed)_

### 6. Dependencies
The profiles capability depends on the following capabilities:
* `/browse` capability: The profiles capability exits into the browse capability when a profile is selected.
* `/account/plan` capability: The profiles capability exits into the account/plan capability when a profile is selected, for member and premium roles.

### 7. Implicit metric
_(no evidence observed)_