import os
import json
import base64
import httpx
import re
import asyncio
from typing import Dict, List, Optional

class AIAgent:
    def __init__(self, groq_api_key: str = None):
        self.api_key = groq_api_key or os.getenv('GROQ_API_KEY')
        self.vision_model = os.getenv('GROQ_VISION_MODEL', "llama-3.2-11b-vision-preview")
        self.fallback_model = os.getenv('GROQ_FALLBACK_MODEL', "llama-3.2-11b-vision-preview")
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'

    def _debug_print(self, message: str):
        if self.debug:
            print(f"[AGENT] {message}")

    def get_image_base64(self, image_url: str) -> Optional[str]:
        try:
            if image_url.startswith('data:image/'):
                parts = image_url.split(',')
                if len(parts) > 1:
                    return parts[1]
            
            response = httpx.get(image_url, timeout=10)
            if response.status_code == 200:
                return base64.b64encode(response.content).decode('utf-8')
        except Exception as e:
            self._debug_print(f"Error fetching image: {e}")
        return None

    async def solve_challenge(self, challenge_data: Dict) -> Dict:
        request_type = challenge_data.get('request_type')
        question = challenge_data.get('requester_question', {}).get('en', 'Unknown')
        tasklist = challenge_data.get('tasklist', [])

        if not self.api_key:
            self._debug_print("No GROQ_API_KEY provided")
            return self._get_fallback_answer(request_type, tasklist[0] if tasklist else None)

        if not tasklist:
            return self._get_fallback_answer(request_type)

        try:
            return await self._solve_with_groq_vision(challenge_data)
        except Exception as e:
            self._debug_print(f"Error solving with Groq: {e}")
            return self._get_fallback_answer(request_type, tasklist[0] if tasklist else None)

    async def _solve_with_groq_vision(self, challenge_data: Dict) -> Dict:
        request_type = challenge_data.get('request_type')
        question = challenge_data.get('requester_question', {}).get('en', 'Unknown')
        tasklist = challenge_data.get('tasklist', [])
        
        # Optimize for single batch request
        if request_type in ['image_label_binary', 'image_label_area_select', 'image_drag_drop']:
            main_task = tasklist[0]
            image_url = main_task.get('datapoint_uri')
            
            # For binary, we need to check each image. Groq vision can handle multiple images or a grid.
            # However, hCaptcha often sends individual URLs for binary.
            if request_type == 'image_label_binary':
                # Batch process if possible, or parallel requests
                tasks = []
                for i, task in enumerate(tasklist):
                    url = task.get('datapoint_uri')
                    if url:
                        tasks.append(self._solve_single_binary(question, url, i))
                
                results = await asyncio.gather(*tasks)
                answers = [r for r in results if r]
                return {'answers': answers}
            
            elif request_type == 'image_label_area_select':
                # Single image
                if not image_url: return self._get_fallback_answer(request_type, main_task)
                image_base64 = self.get_image_base64(image_url)
                if not image_base64: return self._get_fallback_answer(request_type, main_task)
                
                return await self._solve_complex_groq(question, image_base64, request_type, main_task)

            elif request_type == 'image_drag_drop':
                if not image_url: return self._get_fallback_answer(request_type, main_task)
                image_base64 = self.get_image_base64(image_url)
                if not image_base64: return self._get_fallback_answer(request_type, main_task)
                
                return await self._solve_complex_groq(question, image_base64, request_type, main_task)

        return self._get_fallback_answer(request_type)

    async def _solve_single_binary(self, question: str, image_url: str, index: int) -> Optional[Dict]:
        image_base64 = self.get_image_base64(image_url)
        if not image_base64: return None
        
        prompt = f"Does this image contain {question}? Answer YES or NO."
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.vision_model,
                "messages": [
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]}
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"].upper()
                    if "YES" in content:
                        return {'x': index % 3, 'y': index // 3} # Assuming 3x3 grid logic for return format compatibility
        except Exception:
            pass
        return None

    async def _solve_complex_groq(self, question: str, image_base64: str, request_type: str, main_task: Dict) -> Dict:
        prompt = self._get_prompt(request_type, question, main_task)
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.vision_model,
                "messages": [
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]}
                ],
                "max_tokens": 500,
                "temperature": 0.1
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    # Extract JSON
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
        except Exception as e:
            self._debug_print(f"Complex solve error: {e}")
            
        return self._get_fallback_answer(request_type, main_task)

    def _get_prompt(self, request_type: str, question: str, main_task: Dict) -> str:
        if request_type == 'image_label_area_select':
            return f"""Question: {question}
Click on the object. Return JSON: {{"answers": [{{"x": 200, "y": 150}}]}}"""
        elif request_type == 'image_drag_drop':
             return f"""Question: {question}
Where should the object go? Return JSON: {{"answers": [{{"to_x": 150, "to_y": 150}}]}}"""
        return "Return JSON answers."

    def _get_fallback_answer(self, request_type: str, main_task: Dict = None) -> Dict:
        # Simple center click fallback
        if request_type == 'image_label_area_select':
            return {"answers": [{"x": 200, "y": 150}]}
        elif request_type == 'image_drag_drop':
            return {"answers": [{"to_x": 150, "to_y": 150}]}
        return {"answers": []}
