// Source.cpp : This file contains the 'main' function. Program execution begins and ends there.
//
#include <stdio.h>
#include <wchar.h>
#include <tchar.h>
#include "windows.h"
#include "Mmdeviceapi.h"
#include "PolicyConfig.h"
#include "Propidl.h"
#include "Functiondiscoverykeys_devpkey.h"

#include <map>
//#include <thread>
//#include <chrono>
#include <string>
#include <iostream>

static std::string WCharToMByte(LPCWSTR lpcwszStr)
{
    std::string str;
    DWORD dwMinSize = 0;
    LPSTR lpszStr = NULL;
    dwMinSize = WideCharToMultiByte(CP_OEMCP, NULL, lpcwszStr, -1, NULL, 0, NULL, FALSE);
    if (0 == dwMinSize)
    {
        return FALSE;
    }
    lpszStr = new char[dwMinSize];
    WideCharToMultiByte(CP_OEMCP, NULL, lpcwszStr, -1, lpszStr, dwMinSize, NULL, FALSE);
    str = lpszStr;
    delete[] lpszStr;
    return str;
}

static std::wstring string_to_wstring(const std::string& str)
{
    std::wstring result;
    int len = MultiByteToWideChar(CP_ACP, 0, str.c_str(), -1, NULL, 0);
    wchar_t* wstr = new wchar_t[len + 1];
    memset(wstr, 0, len + 1);
    MultiByteToWideChar(CP_ACP, 0, str.c_str(), -1, wstr, len);
    wstr[len] = '\0';
    result.append(wstr);
    delete[] wstr;
    return result;
}

HRESULT SetDefaultAudioPlaybackDevice(LPCWSTR devID)
{
    IPolicyConfigVista* pPolicyConfig;
    ERole reserved = eConsole;

    HRESULT hr = CoCreateInstance(__uuidof(CPolicyConfigVistaClient),
        NULL, CLSCTX_ALL, __uuidof(IPolicyConfigVista), (LPVOID*)&pPolicyConfig);
    if (SUCCEEDED(hr))
    {
        hr = pPolicyConfig->SetDefaultEndpoint(devID, reserved);
        pPolicyConfig->Release();
    }
    return hr;
}


std::map<std::string, std::string> GetAudioOutputDevices()
{
    std::map<std::string, std::string> all_audio_output_devices_map;

    HRESULT hr = CoInitialize(NULL);
    if (SUCCEEDED(hr))
    {
        IMMDeviceEnumerator* pEnum = NULL;
        // Create a multimedia device enumerator.
        hr = CoCreateInstance(__uuidof(MMDeviceEnumerator), NULL,
            CLSCTX_ALL, __uuidof(IMMDeviceEnumerator), (void**)&pEnum);
        if (SUCCEEDED(hr))
        {
            IMMDeviceCollection* pDevices;
            // Enumerate the output devices.
            hr = pEnum->EnumAudioEndpoints(eRender, DEVICE_STATE_ACTIVE, &pDevices);
            if (SUCCEEDED(hr))
            {
                UINT count;
                pDevices->GetCount(&count);
                if (SUCCEEDED(hr))
                {
                    for (UINT i = 0; i < count; i++)
                    {
                        IMMDevice* pDevice;
                        hr = pDevices->Item(i, &pDevice);
                        if (SUCCEEDED(hr))
                        {
                            LPWSTR wstrID = NULL;
                            hr = pDevice->GetId(&wstrID);
                            if (SUCCEEDED(hr))
                            {
                                IPropertyStore* pStore;
                                hr = pDevice->OpenPropertyStore(STGM_READ, &pStore);
                                if (SUCCEEDED(hr))
                                {
                                    PROPVARIANT friendlyName;
                                    PropVariantInit(&friendlyName);
                                    hr = pStore->GetValue(PKEY_Device_FriendlyName, &friendlyName);
                                    if (SUCCEEDED(hr))
                                    {
                                        std::string devices_name = WCharToMByte(friendlyName.pwszVal);
                                        std::string devices_id = WCharToMByte(wstrID);
                                        std::string map_key = std::to_string(i) + " " + devices_name;

                                        all_audio_output_devices_map[map_key] = devices_id;

                                        PropVariantClear(&friendlyName);
                                    }
                                    pStore->Release();
                                }
                            }
                            pDevice->Release();
                        }
                    }
                }
                pDevices->Release();
            }
            pEnum->Release();
        }
    }

    return all_audio_output_devices_map;
}

void printAllDevice() {
    std::map<std::string, std::string> all_audio_output_devices_map = GetAudioOutputDevices();
    std::cout << "Audio Playout Devices: " << std::endl;
    for (auto iter = all_audio_output_devices_map.begin(); iter != all_audio_output_devices_map.end(); iter++)
    {
        std::wstring w_select_alert_playout_device_id = string_to_wstring(iter->second);
        if (w_select_alert_playout_device_id.empty()) continue;
        std::cout << iter->first << std::endl;
    }
}

void setDefaultDevice(std::string name) { //set the default device to which the name contains [input string]
    LPWSTR devID = { 0 }; // to store decive ID
    std::string devName; // to store device name
    int count = 0; // to count the number of the devices whose name contain [input string]
    std::map<std::string, std::string> all_audio_output_devices_map = GetAudioOutputDevices();

    for (auto iter = all_audio_output_devices_map.begin(); iter != all_audio_output_devices_map.end(); iter++)
    {

        std::wstring w_select_alert_playout_device_id = string_to_wstring(iter->second);
        if (w_select_alert_playout_device_id.empty())
            continue;

        //std::cout << "Audio Playout Devices: " << iter->first << std::endl;

        if (iter->first.find(name) != iter->first.npos) {
            count++;
            devName = iter->first;
            WCHAR w_buffer_select_alert_playout_device_id[1000] = { 0 };
            wmemcpy_s(w_buffer_select_alert_playout_device_id, 1000, w_select_alert_playout_device_id.c_str(), w_select_alert_playout_device_id.size());
            devID = w_buffer_select_alert_playout_device_id; //change type WCHAR to LPWSTR
        }
    }

    if (count ==0) {
        std::cout << "connot found the device which contain '"<<name<<"', set default sound output device failled!" << std::endl;
    }
    else if(count ==1){
        SetDefaultAudioPlaybackDevice(devID);
        std::cout << "set the default device to " << devName << " successfully!" << std::endl;
    }
    else {
        std::cout << " more than one device contain string "<< name <<" , please give a name more exacter." << std::endl;
    }
}

void printHelpInfo() {
    std::cout << "+++++++++++++++++++++++++++++++++++++   Help   Info  ++++++++++++++++++++++++++++++++++++++\n\n";
    std::cout << "-p             : print all available output device\n-s  [name]     : set the device whose name contais [name] to default device\n\n\n";
    std::cout << "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n";
}
int main(int argc, char* argv[])
{

    if (argc == 1) {
        printHelpInfo();
    }
    else {
        std::string cmmandKey = argv[1];
        if(cmmandKey == "-p"){
            printAllDevice();
        }
        else if(cmmandKey == "-s"){
            if (argc < 3) { std::cout << "no input parameter for command -s\n"; return 1; }
            setDefaultDevice(argv[2]);
        }
        else {
            printHelpInfo();
        }
    }
    
    
    

    return 0;
}