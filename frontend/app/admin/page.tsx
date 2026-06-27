import AdminConsoleV2 from "./AdminConsoleV2";

// Admin console v1 (#49) — Members & roles + Data sources. The route gate +
// admin chrome live in the client component (it reads the live Clerk org role);
// the backend require_admin is the authoritative wall on every write.
export default function AdminPage() {
  return <AdminConsoleV2 />;
}
