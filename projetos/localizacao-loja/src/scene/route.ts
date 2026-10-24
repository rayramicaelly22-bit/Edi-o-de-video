// Amostragem da rota (coordenadas locais: x = leste, z = -norte, em metros).

export type Route = {points: [number, number][]; along: number[]; length: number};

export const routePoint = (route: Route, s: number): [number, number] => {
  const {points, along} = route;
  if (s <= 0) return points[0];
  if (s >= route.length) return points[points.length - 1];
  let lo = 0;
  let hi = along.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (along[mid] <= s) lo = mid;
    else hi = mid;
  }
  const k = (s - along[lo]) / Math.max(along[hi] - along[lo], 1e-6);
  return [points[lo][0] + (points[hi][0] - points[lo][0]) * k, points[lo][1] + (points[hi][1] - points[lo][1]) * k];
};

// Rumo em graus (0 = norte, 90 = leste) de a para b.
export const bearing = (a: [number, number], b: [number, number]) => {
  const east = b[0] - a[0];
  const north = -(b[1] - a[1]);
  return (Math.atan2(east, north) * 180) / Math.PI;
};

// Rumo suavizado: olha de um ponto atrás para um ponto à frente na rota.
export const routeBearing = (route: Route, s: number, back = 160, ahead = 320) => {
  const a = routePoint(route, s - back);
  const b = routePoint(route, s + ahead);
  const extraA = Math.max(0, back - s);
  const extraB = Math.max(0, s + ahead - route.length);
  if (extraA > 0 || extraB > 0) {
    // nas pontas, usa a direção local para não "travar" o rumo
    const a2 = routePoint(route, Math.max(0, s - back));
    const b2 = routePoint(route, Math.min(route.length, Math.max(s + ahead, 40)));
    return bearing(a2, b2);
  }
  return bearing(a, b);
};
