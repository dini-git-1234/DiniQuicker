import React, { useEffect, useRef, useState } from 'react';

const GovMap = (address) => {
  const [error, setError] = useState(null);
  const [addressInput, setAddressInput] = useState('');
  const [siteInfo, setSiteInfo] = useState(null);
  const isInitialized = useRef(false);

  useEffect(() => {
    const loadGovmapScript = () => {
      return new Promise((resolve, reject) => {
        if (window.govmap) {
          resolve();
          return;
        }
        const script = document.createElement('script');
        script.src = `https://www.govmap.gov.il/govmap/api/govmap.api.js`;
        script.async = true;
        script.onload = () => (window.govmap ? resolve() : reject());
        script.onerror = () => reject(new Error("Failed to load Govmap script"));
        document.head.appendChild(script);
      });
    };

    loadGovmapScript()
      .then(() => {
        if (!isInitialized.current) {
          window.govmap.createMap('govmap-container', {
            token: 'cbeda8ea-2ef1-4a1b-b853-80fd565a8d94',
            layers: ["PARCELS", "CON_SITE"],
            showSelectedFeature: true,
            zoomLevel: 10,
            center: { x: 180000, y: 660000 }
          });

          window.govmap.onEvent(window.govmap.events.CLICK, (e) => {
            identifyContamination(e.data.x, e.data.y);
          });

          isInitialized.current = true;
        }
      })
      .catch((err) => {
        setError("שגיאה בטעינת המפה.");
      });
  }, []);

  const identifyContamination = (x, y) => {
    window.govmap.getLayerData({
      layerName: 'CON_SITE',
      x: x,
      y: y,
      tolerance: 10
    }).then((response) => {
      if (response.data && response.data.length > 0) {
        setSiteInfo(response.data[0].values);
      } else {
        setSiteInfo(null);
      }
    });
  };

  const handleSearch = () => {
    if (!window.govmap) {
      console.error("Govmap API not loaded");
      return;
    }

    if (!addressInput) {
      alert("נא להזין כתובת לחיפוש");
      return;
    }

    // נסיון להשתמש ב-geocode, שהיא הפונקציה המומלצת לחיפוש כתובת
    try {
      window.govmap.geocode({
        keyword: addressInput,
        type: window.govmap.geocodeType.FullAddress, // חיפוש כתובת מלאה
        isCenter: true, // גורם למפה להתמקד בתוצאה
        zoomLevel: 16
      });
    } catch (err) {
      // אם geocode לא קיימת, ננסה את searchAndCenter כגיבוי
      console.log("Geocode failed, trying searchAndCenter...");
      if (typeof window.govmap.searchAndCenter === 'function') {
        window.govmap.searchAndCenter({
          type: 1,
          value: addressInput,
          zoomLevel: 16
        });
      } else {
        console.warn("חיפוש עדיין לא זמין. המתינו לסיום טעינת המפה.");
      }
    }
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', direction: 'rtl', padding: '10px' }}>
      {/* שינוי מ-form ל-div למניעת שגיאת קינון */}
      <div style={{ marginBottom: '15px', display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={addressInput}
          onChange={(e) => setAddressInput(e.target.value)}
          placeholder="עיר רחוב ומספר בית..."
          style={{ padding: '8px', flex: 1, border: '1px solid #ccc', borderRadius: '4px' }}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()} // מאפשר חיפוש בלחיצה על Enter
        />
        <button 
          type="button" // חשוב להגדיר כ-button כדי שלא יגיש את ה-ReportForm הראשי
          onClick={handleSearch}
          style={{ padding: '8px 15px', backgroundColor: '#007bff', color: '#white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          חפש כתובת
        </button>
      </div>

      {siteInfo && (
        <div style={{ backgroundColor: '#fff3cd', border: '1px solid #ffeeba', padding: '10px', marginBottom: '10px', borderRadius: '5px' }}>
          <strong>⚠️ מידע על אתר חשוד בזיהום קרקע:</strong>
          <ul style={{ margin: '5px 0', fontSize: '0.9em' }}>
            {Object.entries(siteInfo).map(([key, val]) => (
              <li key={key}><strong>{key}:</strong> {val}</li>
            ))}
          </ul>
        </div>
      )}

      {error && <div style={{ color: 'red' }}>{error}</div>}

      <div 
        id="govmap-container" 
        style={{ width: '100%', height: '500px', border: '1px solid #ccc', borderRadius: '8px' }} 
      />
    </div>
  );
};

export default GovMap;