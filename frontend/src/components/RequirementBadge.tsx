import { Link } from "react-router-dom";

export function RequirementBadge({ id }: { id: string }) {
  return (
    <Link className="requirement-badge" to={`/requirements?id=${encodeURIComponent(id)}`}>
      需求 {id}
    </Link>
  );
}
