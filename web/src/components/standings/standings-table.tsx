import { type StandingsQuery } from "@/graphql/generated";

type Row = StandingsQuery["standings"][number];

/**
 * StandingsTable (DESIGN.md §3.3/§4.2): a real <table> on desktop — mono
 * tabular numeric columns, right-aligned, azure left-rail on row hover.
 * On mobile each row collapses into a "grid slot" card.
 */
export function StandingsTable({ rows, season }: { rows: readonly Row[]; season: number }) {
  return (
    <>
      {/* Desktop table */}
      <table className="hidden w-full border-collapse md:table">
        <caption className="sr-only">
          Formula 1 drivers&apos; championship standings for {season}
        </caption>
        <thead>
          <tr className="border-b border-hairline-2">
            <th scope="col" className="instrument px-3 py-2 text-left text-micro text-text-faint">
              P
            </th>
            <th scope="col" className="instrument px-3 py-2 text-left text-micro text-text-faint">
              Driver
            </th>
            <th scope="col" className="instrument px-3 py-2 text-left text-micro text-text-faint">
              Constructor
            </th>
            <th scope="col" className="instrument px-3 py-2 text-right text-micro text-text-faint">
              PTS
            </th>
            <th scope="col" className="instrument px-3 py-2 text-right text-micro text-text-faint">
              W
            </th>
            <th scope="col" className="instrument px-3 py-2 text-right text-micro text-text-faint">
              P°
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.driver.id}
              className="border-b border-hairline shadow-[inset_0_0_0_0_transparent] transition-[box-shadow,background-color] duration-120 hover:bg-surface-1 hover:shadow-[inset_3px_0_0_0_var(--color-azure)]"
            >
              <td className="tabular px-3 py-2.5 font-mono text-meta text-text-dim">{row.position}</td>
              <td className="px-3 py-2.5 text-ui text-text">
                <span className="font-medium">{row.driver.fullName}</span>{" "}
                <span className="instrument text-micro text-text-faint">{row.driver.code}</span>
              </td>
              <td className="px-3 py-2.5 text-ui text-text-dim">{row.driver.constructor.name}</td>
              <td className="tabular px-3 py-2.5 text-right font-mono text-meta text-text">
                {row.points}
              </td>
              <td className="tabular px-3 py-2.5 text-right font-mono text-meta text-text-dim">
                {row.wins}
              </td>
              <td className="tabular px-3 py-2.5 text-right font-mono text-meta text-text-dim">
                {row.podiums}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Mobile: each row becomes a grid-slot card */}
      <ul className="space-y-2 md:hidden" aria-label={`Drivers' standings ${season}`}>
        {rows.map((row) => (
          <li
            key={row.driver.id}
            className="flex items-center gap-3 rounded-lg border border-hairline bg-surface-1 px-4 py-3"
          >
            <span className="tabular instrument w-10 shrink-0 border-r border-hairline pr-3 font-mono text-h3 text-text-dim">
              P{row.position}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-ui font-medium text-text">
                {row.driver.fullName}
              </span>
              <span className="block text-micro text-text-dim">
                {row.driver.constructor.name} · {row.wins} wins · {row.podiums} podiums
              </span>
            </span>
            <span className="tabular shrink-0 font-mono text-ui text-text">{row.points}pts</span>
          </li>
        ))}
      </ul>
    </>
  );
}
