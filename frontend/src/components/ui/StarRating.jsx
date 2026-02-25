import { FiStar } from "react-icons/fi";
import "./StarRating.css";

export default function StarRating({ value = 0, max = 5, size = 16 }) {
  return (
    <span className="star-rating" aria-label={`${value} out of ${max}`}>
      {Array.from({ length: max }, (_, i) => (
        <FiStar
          key={i}
          size={size}
          className={i < Math.round(value) ? "star--filled" : "star--empty"}
        />
      ))}
      <span className="star-rating__value">{value?.toFixed(1)}</span>
    </span>
  );
}
