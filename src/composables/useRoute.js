export const useRoute = (provider, providerApiKey, customRouteUrl, fetchCustomToken, normalizeCoordinate, routePairKey, cacheAndReturn, getPersistentCacheValue) => {
  class HerePolylineDecoder {
    constructor(encoded) {
      this.encoded = encoded;
      this.index = 0;
      this.lat = 0;
      this.lng = 0;
      this.z = 0;
      this.precision = 5;
      this.thirdDim = 0;
      this.thirdDimPrecision = 0;
      this.headerDecoded = false;
    }

    hasNext() {
      if (!this.headerDecoded) {
        this.decodeHeader();
      }
      return this.index < this.encoded.length;
    }

    next() {
      if (!this.headerDecoded) {
        this.decodeHeader();
      }
      this.lat += this.decodeSigned();
      this.lng += this.decodeSigned();
      if (this.thirdDim) {
        this.z += this.decodeSigned();
      }
      return {
        lat: this.lat / Math.pow(10, this.precision),
        lng: this.lng / Math.pow(10, this.precision),
      };
    }

    decodeHeader() {
      const header = this.decodeUnsigned();
      this.precision = header & 15;
      this.thirdDim = (header >> 4) & 7;
      this.thirdDimPrecision = (header >> 7) & 15;
      this.headerDecoded = true;
    }

    decodeUnsigned() {
      let result = 0;
      let shift = 0;
      while (this.index < this.encoded.length) {
        const value = this.encoded.charCodeAt(this.index++) - 63;
        result |= (value & 31) << shift;
        if (value < 32) {
          return result;
        }
        shift += 5;
      }
      return result;
    }

    decodeSigned() {
      const result = this.decodeUnsigned();
      return result & 1 ? ~(result >> 1) : result >> 1;
    }
  }

  const decodeHerePolyline = (polyline) => {
    const decoder = new HerePolylineDecoder(polyline);
    const coordinates = [];
    while (decoder.hasNext()) {
      const { lat, lng } = decoder.next();
      coordinates.push([normalizeCoordinate(lng), normalizeCoordinate(lat)]);
    }
    return {
      type: "LineString",
      coordinates,
    };
  };

  const fetchRoute = async (originLat, originLng, destLat, destLng) => {
    const normalizedOriginLat = normalizeCoordinate(originLat);
    const normalizedOriginLng = normalizeCoordinate(originLng);
    const normalizedDestLat = normalizeCoordinate(destLat);
    const normalizedDestLng = normalizeCoordinate(destLng);
    const pairKey = routePairKey(
      normalizedOriginLat,
      normalizedOriginLng,
      normalizedDestLat,
      normalizedDestLng
    );
    const persistentCached = pairKey ? getPersistentCacheValue("route", pairKey) : null;
    if (persistentCached) {
      return persistentCached;
    }

    if (provider.value === "custom") {
      const token = await fetchCustomToken();
      if (!token) {
        return {
          success: false,
          type: "auth_error",
          request: customRouteUrl.value || "getResAppDynamicToken",
          response: "无法获取自定义接口 Token",
        };
      }
      const url = customRouteUrl.value || "routeSearch";
      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: token,
          },
          body: JSON.stringify({
            origin: { lat: normalizedOriginLat, lng: normalizedOriginLng },
            destination: { lat: normalizedDestLat, lng: normalizedDestLng },
            coordType: "wgs84",
          }),
        });
        const body = await response.json();
        if (!response.ok || body?.status !== "OK") {
          return {
            success: false,
            type: "network_error",
            request: url,
            response: JSON.stringify(body),
          };
        }
        const route = body?.result?.routes?.[0];
        if (!route) {
          return {
            success: false,
            type: "no_result",
            request: url,
            response: JSON.stringify(body),
          };
        }
        const geometry = route.geometry
          ? {
              ...route.geometry,
              coordinates: (route.geometry.coordinates || []).map((coord) => [
                normalizeCoordinate(coord?.[0]),
                normalizeCoordinate(coord?.[1]),
              ]),
            }
          : null;
        return cacheAndReturn("route", pairKey, {
          success: true,
          distanceKm: (route.distance / 1000).toFixed(2),
          durationMin: Math.round(route.duration / 60),
          line: geometry,
          origin: { lat: normalizedOriginLat, lng: normalizedOriginLng },
          destination: { lat: normalizedDestLat, lng: normalizedDestLng },
          key: pairKey,
        });
      } catch (error) {
        return {
          success: false,
          type: "network_error",
          request: url,
          response: String(error),
        };
      }
    }

    if (provider.value === "mapbox") {
      const url = `https://api.mapbox.com/directions/v5/mapbox/driving/${normalizedOriginLng},${normalizedOriginLat};${normalizedDestLng},${normalizedDestLat}?geometries=geojson&overview=full&access_token=${providerApiKey.value}`;
      try {
        const response = await fetch(url);
        const body = await response.json();
        if (!response.ok) {
          return {
            success: false,
            type: "network_error",
            request: url,
            response: JSON.stringify(body),
          };
        }
        if (!body.routes || body.routes.length === 0) {
          return {
            success: false,
            type: "no_result",
            request: url,
            response: JSON.stringify(body),
          };
        }
        const route = body.routes[0];
        const geometry = route.geometry
          ? {
              ...route.geometry,
              coordinates: (route.geometry.coordinates || []).map((coord) => [
                normalizeCoordinate(coord?.[0]),
                normalizeCoordinate(coord?.[1]),
              ]),
            }
          : null;

        return cacheAndReturn("route", pairKey, {
          success: true,
          distanceKm: (route.distance / 1000).toFixed(2),
          durationMin: Math.round(route.duration / 60),
          line: geometry,
          origin: { lat: normalizedOriginLat, lng: normalizedOriginLng },
          destination: { lat: normalizedDestLat, lng: normalizedDestLng },
          key: pairKey,
        });
      } catch (error) {
        return {
          success: false,
          type: "network_error",
          request: url,
          response: String(error),
        };
      }
    }

    const url = `https://router.hereapi.com/v8/routes?transportMode=car&origin=${normalizedOriginLat},${normalizedOriginLng}&destination=${normalizedDestLat},${normalizedDestLng}&return=summary,polyline&apiKey=${providerApiKey.value}`;
    try {
      const response = await fetch(url);
      const body = await response.json();
      if (!response.ok) {
        return {
          success: false,
          type: "network_error",
          request: url,
          response: JSON.stringify(body),
        };
      }
      if (!body.routes || body.routes.length === 0) {
        return {
          success: false,
          type: "no_result",
          request: url,
          response: JSON.stringify(body),
        };
      }
      const route = body.routes[0];
      const summary = route.sections?.[0]?.summary;
      const polyline = route.sections?.[0]?.polyline;
      const geometry = polyline ? decodeHerePolyline(polyline) : null;
      return cacheAndReturn("route", pairKey, {
        success: true,
        distanceKm: summary ? (summary.length / 1000).toFixed(2) : "",
        durationMin: summary ? Math.round(summary.duration / 60) : "",
        line: geometry,
        origin: { lat: normalizedOriginLat, lng: normalizedOriginLng },
        destination: { lat: normalizedDestLat, lng: normalizedDestLng },
        key: pairKey,
      });
    } catch (error) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: String(error),
      };
    }
  };

  return {
    fetchRoute,
    decodeHerePolyline
  };
};
