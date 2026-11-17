(() => {
  const elements = {
    citySelect: document.getElementById("city-select"),
    localitySelect: document.getElementById("locality-select"),
    propertySelect: document.getElementById("property-select"),
    selectorStatus: document.getElementById("selector-status"),
    locationSummary: document.getElementById("location-summary"),
    areaInput: document.getElementById("area-input"),
    bedroomsInput: document.getElementById("bedrooms-input"),
    bathroomsInput: document.getElementById("bathrooms-input"),
    ageInput: document.getElementById("age-input"),
    resetFeaturesBtn: document.getElementById("reset-features-btn"),
    predictBtn: document.getElementById("predict-btn"),
    predictionForm: document.getElementById("prediction-form"),
    globalError: document.getElementById("global-error"),
    globalErrorMessage: document.getElementById("global-error-message"),
    validationError: document.getElementById("validation-error"),
    validationErrorMessage: document.getElementById("validation-error-message"),
    resultContext: document.getElementById("result-context"),
    resultEmpty: document.getElementById("result-empty"),
    resultLoading: document.getElementById("result-loading"),
    resultError: document.getElementById("result-error"),
    resultErrorMessage: document.getElementById("result-error-message"),
    resultPopulated: document.getElementById("result-populated"),
    modelNotice: document.getElementById("model-notice"),
    modelNoticeMessage: document.getElementById("model-notice-message"),
    predictedPriceValue: document.getElementById("predicted-price-value"),
    resultPropertyId: document.getElementById("result-property-id"),
    resultModelVersion: document.getElementById("result-model-version"),
    resultTimestamp: document.getElementById("result-timestamp"),
  };

  let currentProperty = null;
  let isPredicting = false;

  const inrFormatter = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  });

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
      },
      ...options,
    });

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : null;

    if (!response.ok) {
      let detail = `Request failed with status ${response.status}.`;
      if (payload && typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (payload && Array.isArray(payload.detail) && payload.detail.length > 0) {
        detail = payload.detail.map((item) => item.msg || String(item)).join(" ");
      }
      throw new Error(detail);
    }

    return payload;
  }

  function showGlobalError(message) {
    elements.globalErrorMessage.textContent = message;
    elements.globalError.classList.remove("hidden");
  }

  function hideGlobalError() {
    elements.globalError.classList.add("hidden");
    elements.globalErrorMessage.textContent = "";
  }

  function showValidationError(message, invalidField = null) {
    clearValidationError();
    elements.validationErrorMessage.textContent = message;
    elements.validationError.classList.remove("hidden");
    if (invalidField) {
      invalidField.setAttribute("aria-invalid", "true");
    }
  }

  function clearValidationError() {
    elements.validationError.classList.add("hidden");
    elements.validationErrorMessage.textContent = "";
    [
      elements.areaInput,
      elements.bedroomsInput,
      elements.bathroomsInput,
      elements.ageInput,
    ].forEach((input) => input.removeAttribute("aria-invalid"));
  }

  function setFeatureInputsDisabled(disabled) {
    elements.areaInput.disabled = disabled;
    elements.bedroomsInput.disabled = disabled;
    elements.bathroomsInput.disabled = disabled;
    elements.ageInput.disabled = disabled;
    elements.resetFeaturesBtn.disabled = disabled;
    elements.predictBtn.disabled = disabled || isPredicting;
  }

  function setResultView(viewName, contextText) {
    elements.resultEmpty.classList.add("hidden");
    elements.resultLoading.classList.add("hidden");
    elements.resultError.classList.add("hidden");
    elements.resultPopulated.classList.add("hidden");

    if (viewName === "empty") {
      elements.resultEmpty.classList.remove("hidden");
    } else if (viewName === "loading") {
      elements.resultLoading.classList.remove("hidden");
    } else if (viewName === "error") {
      elements.resultError.classList.remove("hidden");
    } else if (viewName === "populated") {
      elements.resultPopulated.classList.remove("hidden");
    }

    elements.resultContext.textContent = contextText;
  }

  function populateSelect(selectEl, items, getValue, getLabel, emptyLabel) {
    selectEl.innerHTML = "";

    if (!items || items.length === 0) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = emptyLabel;
      selectEl.appendChild(option);
      selectEl.disabled = true;
      return;
    }

    items.forEach((item) => {
      const option = document.createElement("option");
      option.value = getValue(item);
      option.textContent = getLabel(item);
      selectEl.appendChild(option);
    });
    selectEl.disabled = false;
  }

  function applyPropertyFeatures(property) {
    currentProperty = property;
    elements.areaInput.value = String(property.features.area_sqft);
    elements.bedroomsInput.value = String(property.features.bedrooms);
    elements.bathroomsInput.value = String(property.features.bathrooms);
    elements.ageInput.value = String(property.features.age_years);
    elements.locationSummary.textContent = `${property.city_name} · ${property.locality_name}`;
    clearValidationError();
    setFeatureInputsDisabled(false);
    setResultView("empty", `Selected ${property.id}`);
  }

  function formatTimestamp(isoTimestamp) {
    if (!isoTimestamp) {
      return "—";
    }
    const parsed = new Date(isoTimestamp);
    if (Number.isNaN(parsed.getTime())) {
      return isoTimestamp;
    }
    return parsed.toLocaleString("en-IN", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
      timeZoneName: "short",
    });
  }

  function validateFeatureInputs() {
    const propertyId = elements.propertySelect.value.trim();
    if (!propertyId) {
      return { valid: false, message: "Please select a property first.", field: null };
    }

    const areaRaw = elements.areaInput.value.trim();
    const bedroomsRaw = elements.bedroomsInput.value.trim();
    const bathroomsRaw = elements.bathroomsInput.value.trim();
    const ageRaw = elements.ageInput.value.trim();

    if (!areaRaw) {
      return { valid: false, message: "Area in square feet is required.", field: elements.areaInput };
    }
    const areaSqft = Number(areaRaw);
    if (!Number.isFinite(areaSqft) || areaSqft <= 0 || areaSqft > 100000) {
      return {
        valid: false,
        message: "Area must be a positive number between 1 and 100,000 sq ft.",
        field: elements.areaInput,
      };
    }

    if (!bedroomsRaw) {
      return {
        valid: false,
        message: "Number of bedrooms is required.",
        field: elements.bedroomsInput,
      };
    }
    const bedrooms = Number(bedroomsRaw);
    if (!Number.isInteger(bedrooms) || bedrooms < 1 || bedrooms > 50) {
      return {
        valid: false,
        message: "Bedrooms must be a whole number of 1 or more.",
        field: elements.bedroomsInput,
      };
    }

    if (!bathroomsRaw) {
      return {
        valid: false,
        message: "Number of bathrooms is required.",
        field: elements.bathroomsInput,
      };
    }
    const bathrooms = Number(bathroomsRaw);
    if (!Number.isInteger(bathrooms) || bathrooms < 1 || bathrooms > 50) {
      return {
        valid: false,
        message: "Bathrooms must be a whole number of 1 or more.",
        field: elements.bathroomsInput,
      };
    }

    if (!ageRaw) {
      return {
        valid: false,
        message: "Property age is required.",
        field: elements.ageInput,
      };
    }
    const ageYears = Number(ageRaw);
    if (!Number.isFinite(ageYears) || ageYears < 0 || ageYears > 200) {
      return {
        valid: false,
        message: "Property age must be a nonnegative number (0 to 200 years).",
        field: elements.ageInput,
      };
    }

    return {
      valid: true,
      payload: {
        property_id: propertyId,
        area_sqft: areaSqft,
        bedrooms,
        bathrooms,
        age_years: ageYears,
      },
    };
  }

  function renderPredictionResponse(data) {
    elements.resultPropertyId.textContent = data.property_id || "—";
    elements.resultModelVersion.textContent = data.model_version || "Not configured";
    elements.resultTimestamp.textContent = formatTimestamp(data.timestamp);

    if (data.status === "MODEL_NOT_CONFIGURED" || data.predicted_price_inr === null) {
      elements.modelNoticeMessage.textContent =
        data.message ||
        "Prediction model is not configured yet. Configure a trained model to obtain price estimates.";
      elements.modelNotice.classList.remove("hidden");
      elements.predictedPriceValue.textContent = "Unavailable";
      elements.predictedPriceValue.classList.add("price-value-unavailable");
      setResultView("populated", "Model not configured");
      return;
    }

    elements.modelNotice.classList.add("hidden");
    elements.predictedPriceValue.classList.remove("price-value-unavailable");
    elements.predictedPriceValue.textContent = inrFormatter.format(data.predicted_price_inr);
    setResultView("populated", "Estimate ready");
  }

  async function loadPropertyDetail(propertyId) {
    if (!propertyId) {
      currentProperty = null;
      setFeatureInputsDisabled(true);
      return;
    }

    elements.selectorStatus.textContent = `Loading ${propertyId}`;
    setFeatureInputsDisabled(true);

    try {
      const property = await fetchJson(`/api/properties/${encodeURIComponent(propertyId)}`);
      hideGlobalError();
      applyPropertyFeatures(property);
      elements.selectorStatus.textContent = "Ready";
    } catch (error) {
      elements.selectorStatus.textContent = "Error";
      showGlobalError(error.message);
    }
  }

  async function loadProperties(localityId) {
    if (!localityId) {
      populateSelect(elements.propertySelect, [], (p) => p.id, (p) => p.label, "No properties");
      setFeatureInputsDisabled(true);
      return;
    }

    elements.selectorStatus.textContent = "Loading properties";
    elements.propertySelect.disabled = true;
    setFeatureInputsDisabled(true);

    try {
      const data = await fetchJson(
        `/api/localities/${encodeURIComponent(localityId)}/properties`
      );
      populateSelect(
        elements.propertySelect,
        data.properties,
        (item) => item.id,
        (item) => item.label,
        "No properties available"
      );

      if (data.properties.length > 0) {
        await loadPropertyDetail(elements.propertySelect.value);
      } else {
        elements.selectorStatus.textContent = "No properties";
      }
    } catch (error) {
      elements.selectorStatus.textContent = "Error";
      showGlobalError(error.message);
    }
  }

  async function loadLocalities(cityId) {
    if (!cityId) {
      populateSelect(elements.localitySelect, [], (l) => l.id, (l) => l.name, "No localities");
      setFeatureInputsDisabled(true);
      return;
    }

    elements.selectorStatus.textContent = "Loading localities";
    elements.localitySelect.disabled = true;
    elements.propertySelect.disabled = true;
    setFeatureInputsDisabled(true);

    try {
      const data = await fetchJson(`/api/cities/${encodeURIComponent(cityId)}/localities`);
      populateSelect(
        elements.localitySelect,
        data.localities,
        (item) => item.id,
        (item) => item.name,
        "No localities available"
      );

      if (data.localities.length > 0) {
        await loadProperties(elements.localitySelect.value);
      } else {
        elements.selectorStatus.textContent = "No localities";
      }
    } catch (error) {
      elements.selectorStatus.textContent = "Error";
      showGlobalError(error.message);
    }
  }

  async function loadCities() {
    elements.selectorStatus.textContent = "Loading cities";
    setFeatureInputsDisabled(true);

    try {
      const data = await fetchJson("/api/cities");
      hideGlobalError();
      populateSelect(
        elements.citySelect,
        data.cities,
        (item) => item.id,
        (item) => item.name,
        "No cities available"
      );

      if (data.cities.length > 0) {
        await loadLocalities(elements.citySelect.value);
      } else {
        elements.selectorStatus.textContent = "No cities";
      }
    } catch (error) {
      elements.selectorStatus.textContent = "Error";
      showGlobalError(error.message);
    }
  }

  async function handlePredictSubmit(event) {
    event.preventDefault();
    clearValidationError();

    const validation = validateFeatureInputs();
    if (!validation.valid) {
      showValidationError(validation.message, validation.field);
      return;
    }

    isPredicting = true;
    elements.predictBtn.disabled = true;
    elements.predictBtn.textContent = "Predicting...";
    setResultView("loading", "Request in progress");

    try {
      const result = await fetchJson("/api/predict", {
        method: "POST",
        body: JSON.stringify(validation.payload),
      });
      hideGlobalError();
      renderPredictionResponse(result);
    } catch (error) {
      elements.resultErrorMessage.textContent = error.message;
      setResultView("error", "Error");
    } finally {
      isPredicting = false;
      elements.predictBtn.textContent = "Predict House Price";
      elements.predictBtn.disabled = !currentProperty;
    }
  }

  function bindEvents() {
    elements.citySelect.addEventListener("change", () => {
      loadLocalities(elements.citySelect.value);
    });

    elements.localitySelect.addEventListener("change", () => {
      loadProperties(elements.localitySelect.value);
    });

    elements.propertySelect.addEventListener("change", () => {
      loadPropertyDetail(elements.propertySelect.value);
    });

    elements.resetFeaturesBtn.addEventListener("click", () => {
      if (currentProperty) {
        applyPropertyFeatures(currentProperty);
      }
    });

    [
      elements.areaInput,
      elements.bedroomsInput,
      elements.bathroomsInput,
      elements.ageInput,
    ].forEach((input) => {
      input.addEventListener("input", clearValidationError);
    });

    elements.predictionForm.addEventListener("submit", handlePredictSubmit);
  }

  bindEvents();
  loadCities();
})();
