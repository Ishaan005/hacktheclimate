// Named connected projects in the ECP GSS 2 planning workbook (source rows
// 476, 572 and 790). The reviewed Ballylickey bus is an upstream station
// proxy, not a verified farm terminal or a live electrical connection.

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
    name: 'Ballybane 2 (Glanta Commons) Wind Farm',
    connection: 'Ballylickey 110 kV station proxy',
    limitingRoute: 'Not established for this plant',
  },
  {
    id: 'demo-wind-west',
    name: 'Ballybane 3 (Glanta Commons) Wind Farm',
    connection: 'Ballylickey 110 kV station proxy',
    limitingRoute: 'Not established for this plant',
  },
  {
    id: 'demo-wind-kealkil',
    name: 'Kealkil (Curraglass) (1)',
    connection: 'Ballylickey 110 kV station proxy',
    limitingRoute: 'Not established for this plant',
  },
];

export function siteById(id: string | null): DemoSite | undefined {
  return DEMO_SITES.find((site) => site.id === id);
}
