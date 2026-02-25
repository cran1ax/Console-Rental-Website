import "./StatusBadge.css";

const VARIANT_MAP = {
  /* rental status */
  pending: "warning",
  confirmed: "info",
  active: "success",
  returned: "neutral",
  cancelled: "neutral",
  late: "danger",
  overdue: "danger",
  /* payment */
  unpaid: "warning",
  partially_paid: "warning",
  paid: "success",
  refunded: "info",
};

export default function StatusBadge({ status }) {
  const variant = VARIANT_MAP[status?.toLowerCase()] || "neutral";
  const label = status?.replace(/_/g, " ") || "—";

  return <span className={`badge badge--${variant}`}>{label}</span>;
}
