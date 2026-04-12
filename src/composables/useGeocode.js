import { ref } from 'vue';

export const useGeocode = (provider, providerApiKey, customGeocodeUrl, fetchCustomToken, normalizeCoordinate, coordPairKey, cacheAndReturn, getPersistentCacheValue) => {
  const geocodeAddress = async (address) => {
    const requestKey = String(address ?? "").trim();
    const persistentCached = getPersistentCacheValue("geocode", requestKey);
    if (persistentCached) {
      return persistentCached;
    }

    const encoded = encodeURIComponent(address);
    if (provider.value === "custom") {
      const token = await fetchCustomToken();
      if (!token) {
        return {
          success: false,
          type: "auth_error",
          request: customGeocodeUrl.value || "getResAppDynamicToken",
          response: "无法获取自定义接口 Token",
        };
      }
      const url = customGeocodeUrl.value || "geographicSearch";
      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: token,
          },
          body: JSON.stringify({
            address,
            language: "en",
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
        const location = body?.result?.geometry?.location;
        if (!location || location.lat == null || location.lng == null) {
          return {
            success: false,
            type: "no_result",
            request: url,
            response: JSON.stringify(body),
          };
        }
        const lat = normalizeCoordinate(location.lat);
        const lng = normalizeCoordinate(location.lng);
        return cacheAndReturn("geocode", requestKey, {
          success: true,
          lat,
          lng,
          key: coordPairKey(lat, lng),
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
      const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encoded}.json?access_token=${providerApiKey.value}`;
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
        if (!body.features || body.features.length === 0) {
          return {
            success: false,
            type: "no_result",
            request: url,
            response: JSON.stringify(body),
          };
        }
        const [lngRaw, latRaw] = body.features[0].center || [];
        const lat = normalizeCoordinate(latRaw);
        const lng = normalizeCoordinate(lngRaw);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
          return {
            success: false,
            type: "no_result",
            request: url,
            response: JSON.stringify(body),
          };
        }
        return cacheAndReturn("geocode", requestKey, {
          success: true,
          lat,
          lng,
          key: coordPairKey(lat, lng),
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

    const url = `https://geocode.search.hereapi.com/v1/geocode?q=${encoded}&apiKey=${providerApiKey.value}`;
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
      if (!body.items || body.items.length === 0) {
        return {
          success: false,
          type: "no_result",
          request: url,
          response: JSON.stringify(body),
        };
      }
      const { lat: latRaw, lng: lngRaw } = body.items[0].position || {};
      const lat = normalizeCoordinate(latRaw);
      const lng = normalizeCoordinate(lngRaw);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        return {
          success: false,
          type: "no_result",
          request: url,
          response: JSON.stringify(body),
        };
      }
      return cacheAndReturn("geocode", requestKey, {
        success: true,
        lat,
        lng,
        key: coordPairKey(lat, lng),
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
    geocodeAddress
  };
};
