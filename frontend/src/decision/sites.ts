// Demonstration sites for the precise grid / site view. Invented names on
// real route names; not live connections. A backend site list replaces this.

export type DemoSite = {
  id: string;
  name: string;
  // Connection point and voltage, as the operator would name it.
  connection: string;
  // Route that limits the site's export.
  limitingRoute: string;
};

export const DEMO_SITES: DemoSite[] = [
  {
    id: 'demo-wind-north-west',
    name: 'Demonstration wind farm A (north-west)',
    connection: 'Srananagh 110 kV',
    limitingRoute: 'Flagford–Srananagh 220 kV',
  },
  {
    id: 'demo-wind-west',
    name: 'Demonstration wind farm B (west)',
    connection: 'Cashla 110 kV',
    limitingRoute: 'Cashla–Flagford 220 kV',
  },
  {
    id: 'demo-solar-south',
    name: 'Demonstration solar farm C (south)',
    connection: 'Great Island 110 kV',
    limitingRoute: 'Great Island–Kellis 220 kV',
  },
];

export function siteById(id: string | null): DemoSite | undefined {
  return DEMO_SITES.find((site) => site.id === id);
}
