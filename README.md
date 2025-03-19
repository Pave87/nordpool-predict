# Nordpool Prediction for Home Assistant

## About

This integration loads and creates sensor with Nordpool prediction data created and provided by [vividfog's nordpool-predict-fi](https://github.com/vividfog/nordpool-predict-fi) project.

This data can be usefull when trying to optimise your energy usage.

Note data loaded is speculation based on inputs used. You can read more from [nordpool-predict-fi](https://github.com/vividfog/nordpool-predict-fi) project.

Please if you run into any issues with functionalty or any other feedback create an issue.

This is my learning project of Home Assistant integrations and Python.

## Installation

### Option 1: HACS

Add this repository to your HACS "https://github.com/Pave87/nordpool-predict"

Look for `Nordpool Prediction` and install

Restart Home Assistant

### Option 2: Manual

You can download and copy nordpool_prediction folder to custom_components in your Home Assistant installation.

## Configuration

Go to `Integrations`

Select `Add Integration`

Look for `Nordpool Prediction`

Theres GUI configuration.

Set sensor name and update interval.

You can also define additioonal costs template and Norpool sensor with actual prices. These are optional.

Template should accept any same template as Nordpool sensor.

If you define Nordpool sensor this is used to estimate accuracy of predictions that now have real price.

## Known issues

At start of Home Assistant actual Nordpool sensor might not have loaded yet when trying to load comparison data. This will load to warning at startup.

After setting up if you open `Configure` of this sensor `additonal costs` and `nordpool` sensor are empty. Those are still configured.
