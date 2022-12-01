## Auto check in script for CordCloud

This is a script that will automatically check in your CordCloud account and get the traffic every day.

## `Usage`
You have two methods to use this script:

1. Run the script in your machine.  
`python AutoCheckIn.py --username=<username> --password=<password> --cookie=<cookie> [--keep-cookie]`  
`username`: Your CordCloud username.Required.  
`password`: Your CordCloud password.Required.  
`cookie`: Due to CordCloud have been protected by the cloudflare, you should manually get the passed cookie of cloudflare The cookie named `cf-clearance`(eg:`cf_clearance=ccioMyG8gG24Nu2xg_FEvzqTrqMcNz9lQAgUdIipCs0-1669178887-0-160`).  
`keep-cookie`: If you want to keep the cookie file, you can use this option.
***
2. Run the script in Github Actions.(recommended)  
First, fork this repository to your own repository.  
Then update the cron time you want in you Github Actions workflow file.  
And set the `USERNAME` , `PASSWORD` and `COOKIE` in the Github Actions secrets  which are in the repository settings rather than github settings.
`Settings->Secrets->Actions->New repository secret`.  
All done! :smile_cat: :smile_cat: :smile_cat:
***
3. If you have any question, welcome to post issues!
```yaml
on:
  schedule:
    - cron: '0 16 * * *'
```
