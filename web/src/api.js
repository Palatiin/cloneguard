// File: src/api.js
// Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
// Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
// Date: 2023-04-29
// Description: API request wrapper.

export const api_url = "http://0.0.0.0:8000/api/v1"


export function load(endpoint, params){
    const url = new URL(api_url + endpoint);
    url.search = new URLSearchParams(params).toString();
    console.log(`Requesting ${url}`);
    return fetch(url, {
        mode: "cors"
    })
        .then((res) => {
            return res.json();
        })
        .then((res) => {
            return {
                data: res,
                success: true,
                error: null
            };
        })
        .catch(e => {
            return {
                data: null,
                success: false,
                error: e
            };
        });
}

export function post(endpoint, params=null){
    return fetch(new URL(api_url + endpoint), {
        method: "POST",
        body: JSON.stringify(params),
        headers: {
            'Content-Type': 'application/json'
        },
        mode: "cors",
    })
        .then((res) => {
            return res.json();
        })
        .then((res) => {
            return {
                data: res,
                success: res.error == null,
                error: null
            };
        })
        .catch((e) => {
            return {
                data: null,
                success: false,
                error: e
            };
        })
}
