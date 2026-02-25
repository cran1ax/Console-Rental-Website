import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { SiPlaystation } from "react-icons/si";
import { rentalsAPI } from "../../api";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import "./Browse.css";

const CONSOLE_TYPES = [
  { value: "", label: "All Types" },
  { value: "ps5", label: "PS5" },
  { value: "ps5_digital", label: "PS5 Digital" },
  { value: "ps4_pro", label: "PS4 Pro" },
  { value: "ps4_slim", label: "PS4 Slim" },
  { value: "ps4", label: "PS4" },
];

export default function ConsolesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [consoles, setConsoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState(searchParams.get("console_type") || "");

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (typeFilter) params.console_type = typeFilter;
    rentalsAPI
      .listConsoles(params)
      .then(({ data }) => setConsoles(data.results || data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [typeFilter]);

  const handleTypeChange = (value) => {
    setTypeFilter(value);
    if (value) setSearchParams({ console_type: value });
    else setSearchParams({});
  };

  return (
    <div className="browse">
      <h1>Consoles</h1>

      {/* Filters */}
      <div className="browse__filters">
        {CONSOLE_TYPES.map((t) => (
          <button
            key={t.value}
            className={`filter-chip ${typeFilter === t.value ? "filter-chip--active" : ""}`}
            onClick={() => handleTypeChange(t.value)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : consoles.length === 0 ? (
        <p className="empty">No consoles found.</p>
      ) : (
        <div className="card-grid">
          {consoles.map((c) => (
            <Link to={`/consoles/${c.slug}`} key={c.id} className="card">
              <div className="card__img">
                {c.primary_image?.image ? (
                  <img src={c.primary_image.image} alt={c.name} />
                ) : (
                  <div className="card__img-placeholder">
                    <SiPlaystation />
                  </div>
                )}
              </div>
              <div className="card__body">
                <span className="card__badge">{c.console_type_display}</span>
                <h3 className="card__title">{c.name}</h3>
                <p className="card__price">
                  ₹{c.daily_price}<span>/day</span>
                </p>
                {!c.is_in_stock && <span className="card__oos">Out of Stock</span>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
