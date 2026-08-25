# Deploy the Lambda container (issue #10)

Function: `herop-sdohplace-spatial`  
Role: `herop-sdohplace-spatial-role`  
ECR: `herop-sdohplace-spatial`  
Region: `us-east-2`  
Image, not a zip (geopandas).

Replace `ACCOUNT` with the AWS account id.

## 1. Build and push

From the repo root (Docker must be able to build `linux/amd64`):

```
aws ecr create-repository --repository-name herop-sdohplace-spatial --region us-east-2
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.us-east-2.amazonaws.com
docker build --platform linux/amd64 -t herop-sdohplace-spatial .
docker tag herop-sdohplace-spatial:latest ACCOUNT.dkr.ecr.us-east-2.amazonaws.com/herop-sdohplace-spatial:latest
docker push ACCOUNT.dkr.ecr.us-east-2.amazonaws.com/herop-sdohplace-spatial:latest
```

If `create-repository` says the repo already exists, continue.

Lambda needs permission to pull the image. After the first push, in ECR → repository → Permissions, allow `lambda.amazonaws.com` to `ecr:BatchGetImage` and `ecr:GetDownloadUrlForLayer`, or create the function in the console and let it attach the policy.

## 2. Create or update the function

First time (`iam:PassRole` on `herop-sdohplace-spatial-role` is required):

```
aws lambda create-function --region us-east-2 --function-name herop-sdohplace-spatial --package-type Image --code ImageUri=ACCOUNT.dkr.ecr.us-east-2.amazonaws.com/herop-sdohplace-spatial:latest --role arn:aws:iam::ACCOUNT:role/herop-sdohplace-spatial-role --timeout 900 --memory-size 3008 --ephemeral-storage Size=1024 --environment Variables={UPLOADS_BUCKET=herop-sdohplace-upload}
```

Later image updates:

```
aws lambda update-function-code --region us-east-2 --function-name herop-sdohplace-spatial --image-uri ACCOUNT.dkr.ecr.us-east-2.amazonaws.com/herop-sdohplace-spatial:latest
```

Do not set `AWS_REGION` in the function environment; Lambda sets it.

## 3. Smoke test

Use a dummy invoke that does **not** need a real upload file (unknown `upload_kind` writes the stub `result.json`):

```
aws lambda invoke --region us-east-2 --function-name herop-sdohplace-spatial --invocation-type Event --payload file://examples/invoke-payload.json out.json
```

`InvocationType=Event` is what the manager will use. Put a placeholder object at the payload `s3_key` first, or the stub path still writes `result.json` next to that key. Check the job folder for `result.json`.

Then ping Pengyin for [#11](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/11) (`lambda:InvokeFunction` on the EC2 instance role).
