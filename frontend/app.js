(() => {
  const elements = {
    areaInput: document.getElementById("area-input"),
    bedroomsInput: document.getElementById("bedrooms-input"),
    bathroomsInput: document.getElementById("bathrooms-input"),
    locationInput: document.getElementById("location-input"),
    predictBtn: document.getElementById("predict-btn"),
    predictionForm: document.getElementById("prediction-form"),
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
    resultLocation: document.getElementById("result-location"),
    resultModelVersion: document.getElementById("result-model-version"),
    resultTimestamp: document.getElementById("result-timestamp"),
  };

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
      elements.locationInput,
    ].forEach((input) => input.removeAttribute("aria-invalid"));
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
    const areaRaw = elements.areaInput.value.trim();
    const bedroomsRaw = elements.bedroomsInput.value.trim();
    const bathroomsRaw = elements.bathroomsInput.value.trim();
    const location = elements.locationInput.value.trim();

    if (!areaRaw) {
      return { valid: false, message: "Area in square feet is required.", field: elements.areaInput };
    }
    const areaSqft = Number(areaRaw);
    if (!Number.isFinite(areaSqft) || areaSqft <= 0 || areaSqft > 100000) {
      return {
        valid: false,
        message: "Area must be greater than 0 and at most 100,000 sq ft.",
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

    if (!location || [...location].length > 200) {
      return {
        valid: false,
        message: "Enter a Bengaluru locality of up to 200 characters.",
        field: elements.locationInput,
      };
    }

    return {
      valid: true,
      payload: {
        location,
        area_sqft: areaSqft,
        bedrooms,
        bathrooms,
      },
    };
  }

  function renderPredictionResponse(data) {
    elements.resultLocation.textContent = data.location || "-";
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

  async function handlePredictSubmit(event) {
    event.preventDefault();
    if (elements.predictBtn.disabled) return;
    clearValidationError();

    const validation = validateFeatureInputs();
    if (!validation.valid) {
      showValidationError(validation.message, validation.field);
      return;
    }

    elements.predictBtn.disabled = true;
    elements.predictBtn.textContent = "Predicting...";
    setResultView("loading", "Request in progress");

    try {
      const result = await fetchJson("/api/predict", {
        method: "POST",
        body: JSON.stringify(validation.payload),
      });
      renderPredictionResponse(result);
    } catch (error) {
      elements.resultErrorMessage.textContent = error.message;
      setResultView("error", "Error");
    } finally {
      elements.predictBtn.textContent = "Predict House Price";
      elements.predictBtn.disabled = false;
    }
  }

  function bindEvents() {
    [
      elements.areaInput,
      elements.bedroomsInput,
      elements.bathroomsInput,
      elements.locationInput,
    ].forEach((input) => {
      input.addEventListener("input", clearValidationError);
    });

    elements.predictionForm.addEventListener("submit", handlePredictSubmit);
  }

  bindEvents();
})();
