import AdminGuard from "./admin_guard";

export default function AdminLayout({ children }) {
  return <AdminGuard>{children}</AdminGuard>;
}