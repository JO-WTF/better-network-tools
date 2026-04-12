export const useReverseGeocode = (provider, providerApiKey, normalizeCoordinate, coordPairKey, cacheAndReturn, getPersistentCacheValue) => {
  const extractMapboxAdmin = (feature) => {
    const context = feature.context || [];
    const place = context.find((item) => item.id?.startsWith("place"))?.text || "";
    const district = context.find((item) => item.id?.startsWith("district"))?.text || "";
    const region = context.find((item) => item.id?.startsWith("region"))?.text || "";
    const locality = context.find((item) => item.id?.startsWith("locality"))?.text || "";
    return {
      admin1: region || place || "",
      admin2: place || locality || "",
      admin3: district || locality || "",
    };
  };

  const reverseGeocode = async (lat, lng) => {
    const normalizedLat = normalizeCoordinate(lat);
    const normalizedLng = normalizeCoordinate(lng);
    const requestKey = coordPairKey(normalizedLat, normalizedLng);
    const persistentCached = requestKey
      ? getPersistentCacheValue("reverse", requestKey)
      : null;
    if (persistentCached) {
      return persistentCached;
    }

    if (provider.value === "mapbox") {
      const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${normalizedLng},${normalizedLat}.json?access_token=${providerApiKey.value}`;
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
        const feature = body.features[0];
        const admin = extractMapboxAdmin(feature);
        return cacheAndReturn("reverse", requestKey, {
          success: true,
          address: feature.place_name || "",
          admin1: admin.admin1,
          admin2: admin.admin2,
          admin3: admin.admin3,
          key: requestKey,
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

    const url = `https://revgeocode.search.hereapi.com/v1/revgeocode?at=${normalizedLat},${normalizedLng}&apiKey=${providerApiKey.value}`;
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
      const item = body.items[0];
      const address = item.address || {};
      return cacheAndReturn("reverse", requestKey, {
        success: true,
        address: item.title || "",
        admin1: address.state || "",
        admin2: address.city || address.county || "",
        admin3: address.district || address.subdistrict || "",
        key: requestKey,
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
    reverseGeocode
  };
};
