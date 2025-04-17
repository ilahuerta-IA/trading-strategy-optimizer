// File: assets/clientside.js (Attempt Full Figure Return)

window.dash_clientside = window.dash_clientside || {};

window.dash_clientside.clientside = {
    syncAxes: function(relayoutData1, relayoutData2, figure1, figure2) { // Added figure1, figure2 as inputs
        const ctx = dash_clientside.callback_context;
        if (!ctx.triggered || ctx.triggered.length === 0) {
            return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        }

        const prop_id = ctx.triggered[0].prop_id;
        const relayout_data = ctx.triggered[0].value;
        let triggeredIndex = -1;

        try {
             // Parse ID string to get index
             let triggeredIdObj = JSON.parse(prop_id.split('.')[0].replace(/'/g, '"'));
             triggeredIndex = triggeredIdObj.index;
        } catch (e) {
            console.error("Error parsing trigger ID:", prop_id, e);
            return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        }

        let targetChartIndex = triggeredIndex === 1 ? 2 : 1;
        // console.log("Sync triggered by chart:", triggeredIndex, "Relayout:", relayout_data);

        if (!relayout_data) {
            return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        }

        let newXRange = null;
        let updateNeeded = false;

        if (relayout_data['xaxis.range[0]'] && relayout_data['xaxis.range[1]']) {
            newXRange = [relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']];
            updateNeeded = true;
        } else if (relayout_data['xaxis.range'] && Array.isArray(relayout_data['xaxis.range'])) {
            newXRange = relayout_data['xaxis.range'];
            updateNeeded = true;
        } else if (relayout_data['xaxis.autorange']) {
            newXRange = null; // Autorange
            updateNeeded = true;
        } else if (relayout_data['yaxis.range[0]'] || relayout_data['yaxis.range']) {
             updateNeeded = false; // Ignore y-axis only
        }

        if (!updateNeeded) {
            return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        }

        // console.log("Applying new x range to target chart", targetChartIndex, ":", newXRange);

        // Get the *original* figure object for the target chart
        let targetFigure = targetChartIndex === 1 ? figure1 : figure2;

        // IMPORTANT: Check if the target figure exists and has layout/data
         if (!targetFigure || !targetFigure.layout || !targetFigure.data) {
              console.error("Target figure structure is missing or invalid for chart:", targetChartIndex);
              return [window.dash_clientside.no_update, window.dash_clientside.no_update]; // Avoid errors
         }


        // Create a *new* layout object based on the old one, but with the updated range
        // Avoid mutating the original figure object directly if possible
        let newLayout = {...targetFigure.layout}; // Shallow copy layout
        newLayout.xaxis = {...targetFigure.layout.xaxis}; // Shallow copy xaxis
        newLayout.xaxis.range = newXRange; // Update the range

        // Construct the full figure object to return for the target chart
        // We need to include the original data traces
        let updatedFigure = {
            'data': targetFigure.data, // Keep original data traces
            'layout': newLayout       // Use the new layout with updated range
        };

        // Return the full updated figure for the target chart
        if (targetChartIndex === 1) {
            return [updatedFigure, window.dash_clientside.no_update];
        } else { // targetChartIndex === 2
            return [window.dash_clientside.no_update, updatedFigure];
        }
    }
}